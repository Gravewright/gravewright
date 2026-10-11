import uuid

from django.test import TestCase

from gravewright.maps.services import MapError
from gravewright.maps.models import Scene
from gravewright.table.tests.test_modules import TableModuleTests
from gravewright.tokens.models import Token
from gravewright.tokens.services import command as token_command


class ConditionDurationTests(TestCase):
    setUp = TableModuleTests.setUp
    command = TableModuleTests.command
    state = TableModuleTests.state

    def execute(self, action, request_id=None):
        from gravewright.table.domain import command
        return command(self.campaign.pk,self.gm.pk,'combat',action,
                       {'sceneId':str(self.scene.pk),'version':self.state('combat')['version']},request_id or uuid.uuid4())

    def condition(self, token, label, unit=None, value=1, phase='end', user=None):
        raw={'mapId':str(token.scene_id),'tokenIds':[str(token.pk)],'label':label,'kind':'neutral','visibility':'everyone'}
        if unit:raw['duration']={'type':unit,'value':value,'expires':phase}
        return token_command(self.campaign.pk,(user or self.gm).pk,'condition-add',raw,uuid.uuid4())

    def setup_combat(self):
        self.other=Token.objects.create(scene=self.scene,actor=self.actor,linked=False,snapshot=self.actor.data)
        for token in [self.token,self.other]:
            self.command('combat','add',{'sceneId':str(self.scene.pk),'tokenId':str(token.pk),'version':self.state('combat')['version']})
        self.execute('start')

    def labels(self, token):
        token.refresh_from_db()
        return {c['label']:c for c in token.conditions}

    def test_own_turn_start_and_end_expiration_and_permanent_condition(self):
        self.setup_combat()
        self.condition(self.token,'End','turns')
        self.condition(self.token,'Start','turns',phase='start')
        self.condition(self.token,'Permanent')
        self.execute('next')
        self.assertEqual(set(self.labels(self.token)),{'Start','Permanent'})
        self.execute('next')
        self.assertEqual(set(self.labels(self.token)),{'Permanent'})

    def test_rounds_decrement_only_on_round_boundary_and_only_participants(self):
        self.setup_combat()
        self.condition(self.token,'Rounds','rounds',2)
        self.condition(self.other,'Rounds start','rounds',1,'start')
        outsider=Token.objects.create(scene=self.scene,actor=self.actor)
        self.condition(outsider,'Outside encounter','rounds')
        another_scene=Scene.objects.create(campaign=self.campaign,name='Other scene',width=100,height=100)
        distant=Token.objects.create(scene=another_scene,actor=self.actor)
        self.condition(distant,'Other scene','rounds')
        self.execute('next')
        self.assertEqual(self.labels(self.token)['Rounds']['duration']['remaining'],2)
        self.execute('next')
        self.assertEqual(self.labels(self.token)['Rounds']['duration']['remaining'],1)
        self.assertEqual(self.labels(self.other),{})
        self.execute('next-round')
        self.assertEqual(self.labels(self.token),{})
        self.assertIn('Outside encounter',self.labels(outsider))
        self.assertIn('Other scene',self.labels(distant))

    def test_retries_and_backward_navigation_do_not_tick_again(self):
        self.setup_combat()
        self.condition(self.token,'Countdown','turns',3)
        rid=uuid.uuid4()
        self.execute('next',rid)
        self.execute('next',rid)
        self.assertEqual(self.labels(self.token)['Countdown']['duration']['remaining'],2)
        self.execute('previous')
        self.assertEqual(self.labels(self.token)['Countdown']['duration']['remaining'],2)
        self.execute('stop')
        self.assertEqual(self.labels(self.token)['Countdown']['duration']['remaining'],2)

    def test_invalid_durations_and_read_only_player_are_rejected(self):
        from gravewright.combat.conditions import duration
        for value in [{}, {'type':'turns','value':True}, {'type':'turns','value':1.5},
                      {'type':'rounds','value':0}, {'type':'turns','value':10001},
                      {'type':'turns','value':1,'expires':'later'}, {'type':'turns','value':1,'remaining':3}]:
            with self.subTest(value=value), self.assertRaises(MapError):duration(value)
        self.actor.permissions={'default':'read'};self.actor.save()
        with self.assertRaises(MapError):self.condition(self.token,'Forbidden','turns',user=self.player)
