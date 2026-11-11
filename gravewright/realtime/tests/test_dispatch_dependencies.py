"""Every projection a command changes, for any recipient, is listed in its envelope.

This is the safety net for narrowing dispatch.refreshes: it snapshots each
user's projections before and after real commands and compares them with the
committed envelope. Set GRAVEWRIGHT_PRINT_DEPENDENCIES=1 to print what changed.
"""

import json
import os
from unittest.mock import patch
import uuid

from django.test import TransactionTestCase, override_settings

from gravewright.accounts.models import User
from gravewright.actors import services as actor_services
from gravewright.actors.models import Actor
from gravewright.audio.models import Track
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat import services as chat
from gravewright.compendiums.models import Entry, Pack
from gravewright.items.models import Item
from gravewright.journals import services as journal_services
from gravewright.journals.models import Journal
from gravewright.maps import services as maps
from gravewright.maps.models import Broadcast, Scene
from gravewright.maps.objects import layer_state
from gravewright.realtime import dispatch
from gravewright.table import domain
from gravewright.tokens import services as token_services
from gravewright.tokens.models import Token

MODULES = ('items', 'combat', 'cards', 'audio', 'compendiums', 'clocks', 'clues', 'mindmaps')
FROZEN = 1_800_000_000.0


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DispatchDependencyTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user('deps-gm@example.test', 'password-12345', name='GM')
        self.owner = User.objects.create_user('deps-owner@example.test', 'password-12345', name='Owner')
        self.other = User.objects.create_user('deps-other@example.test', 'password-12345', name='Other')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Dependencies')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.owner, role='player')
        Membership.objects.create(campaign=self.campaign, user=self.other, role='player')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Room', width=512, height=512,
                                          visibility='players')
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Hero', data={},
                                          permissions={'default': 'read', str(self.owner.pk): 'owner'})
        self.token = Token.objects.create(scene=self.scene, actor=self.actor)
        self.hidden = Token.objects.create(scene=self.scene, actor=self.actor, hidden=True, grid_x=3)
        self.track = Track.objects.create(campaign=self.campaign, name='Rain', duration=30, loop=True)
        self.item = Item.objects.create(campaign=self.campaign, name='Rope', type='gear',
                                        system_id=self.campaign.system, data={},
                                        permissions={'default': 'read'})
        self.pack = Pack.objects.create(campaign=self.campaign, name='Shared pack', shared=True)
        self.entry = Entry.objects.create(pack=self.pack, name='Lantern', kind='item',
                                          data={'name': 'Lantern', 'type': 'gear', 'data': {}})
        Journal.objects.create(campaign=self.campaign, title='Notes', creator=self.gm, visibility='public')
        self.users = (self.gm, self.owner, self.other)

    def snapshot(self):
        """Every projection a socket can receive, per user, as canonical JSON."""
        result = {}
        scene = Scene.objects.get(pk=self.scene.pk)
        for user in self.users:
            who = maps.member(self.campaign.pk, user.pk)
            views = {
                'maps.layers': lambda: layer_state(scene, who),
                'tokens': lambda: token_services.state(self.campaign.pk, user.pk, str(scene.pk)),
                'actors': lambda: actor_services.state(self.campaign.pk, user.pk),
                'journals': lambda: journal_services.state(self.campaign.pk, user.pk),
                'maps': lambda: maps.state(self.campaign.pk, user.pk),
                'chat.history': lambda: chat.history(self.campaign.pk, user.pk),
                **{f'resources:{name}': (lambda name=name: domain.state(
                    self.campaign.pk, user.pk, name, str(scene.pk))) for name in MODULES},
            }
            for name, view in views.items():
                try:
                    value = view()
                except Exception as error:  # noqa: BLE001 - a refusal is a projection too
                    value = {'refused': type(error).__name__}
                result[(user.email, name)] = json.dumps(value, sort_keys=True, default=str)
        return result

    def run_command(self, label, call):
        envelopes = []
        with patch('time.time', return_value=FROZEN), \
                patch.object(dispatch, 'send', side_effect=lambda _c, event: envelopes.append(event)):
            before = self.snapshot()
            call()
            after = self.snapshot()
        changed = {name for (_, name), value in after.items() if before[(_, name)] != value}
        refresh = set()
        for event in envelopes:
            if event['type'] == 'room.changes':
                refresh |= set(event['refresh'])
        if os.environ.get('GRAVEWRIGHT_PRINT_DEPENDENCIES'):
            print(f'DEPENDENCIES {label}: changed={sorted(changed)} refresh={sorted(refresh)}')
        with self.subTest(command=label):
            self.assertLessEqual(changed, refresh, f'{label} changed projections missing from its envelope')
        return changed, refresh

    def resource(self, name, action, data, user=None):
        return lambda: domain.command(self.campaign.pk, (user or self.gm).pk, name, action, data, str(uuid.uuid4()))

    def version(self, model, pk):
        return model.objects.get(pk=pk).version

    def test_shared_resource_commands_list_every_changed_projection(self):
        scene = str(self.scene.pk)
        # Narrowed envelopes: each list is what the measured changes justify.
        narrowed = {}
        narrowed['audio/play'] = self.run_command('audio/play', self.resource(
            'audio', 'play', {'sceneId': scene, 'trackId': str(self.track.pk)}))[1]
        from gravewright.audio.models import Playback
        playback = Playback.objects.get(scene=self.scene)
        self.run_command('audio/stop', self.resource('audio', 'stop', {
            'sceneId': scene, 'trackId': str(self.track.pk), 'version': playback.version}))
        changed, _ = self.run_command('audio/spatial-create', self.resource('audio', 'spatial-create', {
            'sceneId': scene, 'trackId': str(self.track.pk), 'x': 10, 'y': 10, 'radius': 25}))
        self.assertIn('maps.layers', changed)
        self.run_command('combat/add', self.resource('combat', 'add', {'sceneId': scene, 'tokenId': str(self.token.pk)}))
        from gravewright.combat.models import Encounter
        encounter = Encounter.objects.get(scene=self.scene)
        self.run_command('combat/start', self.resource('combat', 'start', {'sceneId': scene, 'version': encounter.version}))
        encounter.refresh_from_db()
        narrowed['combat/next'] = self.run_command('combat/next', self.resource(
            'combat', 'next', {'sceneId': scene, 'version': encounter.version}))[1]
        self.run_command('cards/create', self.resource('cards', 'create', {'name': 'Deck', 'cards': ['A', 'B']}))
        from gravewright.cards.models import Card
        card = Card.objects.filter(deck__campaign=self.campaign).order_by('position').first()
        Card.objects.filter(pk=card.pk).update(zone='hand', owner=self.gm)
        changed, _ = self.run_command('cards/place', self.resource('cards', 'place', {
            'id': str(card.pk), 'sceneId': scene, 'x': 20, 'y': 20, 'version': self.version(Card, card.pk)}))
        self.assertIn('maps.layers', changed)
        narrowed['items/update'] = self.run_command('items/update', self.resource('items', 'update', {
            'id': str(self.item.pk), 'name': 'Long rope', 'version': self.item.version}))[1]
        narrowed['compendiums/configure'] = self.run_command('compendiums/configure', self.resource(
            'compendiums', 'configure', {'packId': str(self.pack.pk), 'name': 'Renamed pack',
                                         'version': self.version(Pack, self.pack.pk)}))[1]
        self.run_command('compendiums/import', self.resource('compendiums', 'import', {
            'packId': str(self.pack.pk), 'id': str(self.entry.pk)}))
        self.assertEqual(narrowed, {
            'audio/play': {'resources:audio'},
            'combat/next': {'maps.layers', 'resources:combat'},
            'items/update': {'resources:items'},
            'compendiums/configure': {'resources:compendiums'},
        })

    def test_board_commands_list_every_changed_projection(self):
        self.run_command('tokens/move', lambda: token_services.command(
            self.campaign.pk, self.gm.pk, 'move', {'mapId': str(self.scene.pk), 'id': str(self.token.pk),
                                                   'gridX': 2, 'gridY': 2, 'expectedVersion': self.token.version},
            str(uuid.uuid4())))
        self.run_command('tokens/hidden', lambda: token_services.command(
            self.campaign.pk, self.gm.pk, 'hidden', {'mapId': str(self.scene.pk), 'tokenIds': [str(self.hidden.pk)],
                                                     'hidden': False}, str(uuid.uuid4())))
