"""Token commands keep their write transaction short and their results unchanged."""

import os
import threading
from unittest.mock import patch
import uuid

from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Broadcast, Receipt, Scene
from gravewright.tokens import services
from gravewright.tokens.models import Token

# Statements between BEGIN IMMEDIATE and COMMIT for one GM move in this fixture,
# measured on 2026-11-09 before the change (projection inside the transaction): 12.
# The projection now runs after commit (10 statements in the same fixture).
MOVE_TRANSACTION_STATEMENTS = 12


def in_transaction(queries):
    """SQL executed while the write reservation was held."""
    inside, held = [], False
    for query in queries:
        sql = query['sql']
        if 'BEGIN IMMEDIATE' in sql:
            held = True
        elif sql.startswith(('COMMIT', 'ROLLBACK')):
            held = False
        elif held:
            inside.append(sql)
    return inside


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TokenTransactionBoundaryTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user('token-boundary-gm@example.test', 'password-12345', name='GM')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Token boundaries')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Room', width=512, height=512)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Traveler', data={},
                                          permissions={'default': 'read'})
        self.token = Token.objects.create(scene=self.scene, actor=self.actor)

    def command(self, action, data, request_id=None):
        return services.command(self.campaign.pk, self.gm.pk, action, {'mapId': str(self.scene.pk), **data},
                                request_id or str(uuid.uuid4()))

    def move(self, x=2, request_id=None):
        self.token.refresh_from_db()
        return self.command('move', {'id': str(self.token.pk), 'gridX': x, 'gridY': 1,
                                     'expectedVersion': self.token.version}, request_id)

    def visible(self):
        who = services.member(self.campaign.pk, self.gm.pk)
        return services.rows(Scene.objects.get(pk=self.scene.pk), who)

    def test_move_projection_runs_after_commit(self):
        seen = []
        real = services.rows

        def rows(scene, who):
            seen.append(connection.in_atomic_block)
            return real(scene, who)
        with patch.object(services, 'rows', side_effect=rows):
            self.move()
        self.assertTrue(seen)
        self.assertNotIn(True, seen)

    def test_command_results_keep_their_contract(self):
        placed = self.command('place', {'actorId': str(self.actor.pk), 'gridX': 3, 'gridY': 3})
        self.assertEqual(placed['tokens'], self.visible())
        self.assertEqual(len(placed['createdIds']), 1)
        moved = self.move(4)
        self.assertEqual((moved['tokens'], moved['createdIds']), (self.visible(), []))
        duplicated = self.command('duplicate', {'tokenIds': [str(self.token.pk)]})
        self.assertEqual(duplicated['tokens'], self.visible())
        self.assertEqual(len(duplicated['createdIds']), 1)
        removed = self.command('remove', {'tokenIds': duplicated['createdIds']})
        self.assertEqual((removed['tokens'], removed['createdIds']), (self.visible(), []))
        self.assertNotIn('teleports', moved)

    def test_replay_fast_path_takes_no_write_lock(self):
        request_id = str(uuid.uuid4())
        placed = self.command('place', {'actorId': str(self.actor.pk), 'gridX': 3, 'gridY': 3}, request_id)
        with CaptureQueriesContext(connection) as queries:
            replay = self.command('place', {'actorId': str(self.actor.pk), 'gridX': 3, 'gridY': 3}, request_id)
        self.assertFalse([q for q in queries if 'BEGIN IMMEDIATE' in q['sql']])
        self.assertEqual(replay['createdIds'], placed['createdIds'])
        self.assertEqual(replay['tokens'], self.visible())
        # A replay whose created token is gone filters it, as before.
        Token.objects.filter(pk__in=placed['createdIds']).delete()
        self.assertEqual(self.command('place', {}, request_id)['createdIds'], [])

    def test_concurrent_same_request_id_applies_once(self):
        request_id = str(uuid.uuid4())
        version = self.token.version
        barrier, results, errors = threading.Barrier(2), [], []

        def run():
            try:
                barrier.wait(5)
                results.append(self.command('move', {'id': str(self.token.pk), 'gridX': 5, 'gridY': 1,
                                                     'expectedVersion': version}, request_id))
            except Exception as error:  # noqa: BLE001 - reported by the assertion below
                errors.append(error)
            finally:
                connection.close()
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(Receipt.objects.filter(request_id=request_id).count(), 1)
        self.token.refresh_from_db()
        self.assertEqual((self.token.grid_x, self.token.version), (5, version + 1))

    def test_move_transaction_has_fewer_statements(self):
        self.move(1)  # warm caches that the first command fills
        with CaptureQueriesContext(connection) as queries:
            self.move(3)
        statements = in_transaction(queries)
        if os.environ.get('GRAVEWRIGHT_PRINT_MOVE_STATEMENTS'):
            print('MOVE_TRANSACTION_STATEMENTS', len(statements))
        self.assertLess(len(statements), MOVE_TRANSACTION_STATEMENTS)
