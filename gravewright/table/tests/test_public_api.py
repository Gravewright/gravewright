"""Public imports must retain permission, commit and delivery semantics."""
import uuid
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase
from gravewright.table.tests import test_modules
from gravewright.actors.models import Actor
from gravewright.maps.models import Receipt
from gravewright.chat.models import Message
from api import actors, tokens, maps, journals, resources, chat, dice, events, Context
from api.errors import JournalError, MapError, AuthError


class PublicApiTests(TestCase):
    setUp = test_modules.TableModuleTests.setUp

    def test_exports_are_explicit_service_aliases(self):
        from gravewright.actors import services
        self.assertIs(actors.command,services.command)
        self.assertIs(actors.state,services.state)
        self.assertNotIn('get', actors.__all__)
        self.assertNotIn('apply', maps.__all__)
        context=Context(str(self.campaign.pk),str(self.gm.pk))
        self.assertEqual(context.user_id,self.gm.pk)
        with self.assertRaises(ValueError):Context('invalid',self.gm.pk)

    def test_command_notifies_after_commit_once_and_supports_hooks(self):
        request=uuid.uuid4();changes=[]
        def receiver(sender,change,**kwargs):changes.append((sender,change))
        events.resource_changed.connect(receiver,weak=False,dispatch_uid='public-api-test')
        self.addCleanup(events.resource_changed.disconnect,dispatch_uid='public-api-test')
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                result=actors.command(self.campaign.pk,self.gm.pk,'actor.create',{'name':'Extension actor'},request)
                self.assertFalse(send.called)
                self.assertEqual(changes,[])
            self.assertEqual([c.args[1]['type'] for c in send.call_args_list],['room.actors','room.tokens','room.map_layers'])
            self.assertEqual(changes[0][1].request_id,request)
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                repeated=actors.command(self.campaign.pk,self.gm.pk,'actor.create',{'name':'Ignored retry'},request)
            self.assertEqual(repeated,result)
            self.assertFalse(send.called)
            self.assertEqual(len(changes),1)

    def test_outer_rollback_has_no_delivery_or_hook(self):
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        actors.command(self.campaign.pk,self.gm.pk,'actor.create',{'name':'Rolled back'},uuid.uuid4())
                        raise RuntimeError('Abort enclosing operation')
                except RuntimeError:pass
            self.assertFalse(Actor.objects.filter(name='Rolled back').exists())
            self.assertFalse(send.called)

    def test_native_resources_cannot_bypass_permissions_or_streamer_readonly(self):
        with self.assertRaises(MapError):resources.command(self.campaign.pk,self.player.pk,'cards','create',{'name':'Forbidden','cards':['Ace']},uuid.uuid4())
        from gravewright.campaigns.streamer import issue
        from gravewright.campaigns.models import StreamerLink
        issue(self.gm,self.campaign.pk)
        guest=StreamerLink.objects.latest('expires_at').guest
        with self.assertRaises(JournalError):resources.command(self.campaign.pk,guest.pk,'cards','draw',{},uuid.uuid4())
        with self.assertRaises(AuthError):chat.send(self.campaign.pk,guest.pk,'Forbidden',uuid.uuid4())
        with self.assertRaises(AuthError):dice.roll(self.campaign.pk,guest.pk,'1d6',uuid.uuid4())
        self.campaign.memberships.filter(user=self.player).delete()
        with self.assertRaises(JournalError):actors.state(self.campaign.pk,self.player.pk)

    def test_chat_and_roll_publish_private_audience_after_commit(self):
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                entry=chat.send(self.campaign.pk,self.gm.pk,'/w Player secret',uuid.uuid4())
            event=send.call_args.args[1]
            self.assertEqual(event['type'],'room.message')
            self.assertEqual(set(event['audience']),{str(self.gm.pk),str(self.player.pk)})
            request=uuid.uuid4()
            with self.captureOnCommitCallbacks(execute=True):
                roll=dice.roll(self.campaign.pk,self.player.pk,'1d1+2',request,visibility='gm')
            self.assertEqual(send.call_args.args[1]['message']['id'],roll['id'])
            self.assertEqual(set(send.call_args.args[1]['audience']),{str(self.gm.pk),str(self.player.pk)})
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(dice.roll(self.campaign.pk,self.player.pk,'1d1+2',request,visibility='gm'),roll)
            self.assertFalse(send.called)

    def test_layers_are_projected_and_failed_commands_do_not_notify(self):
        self.scene.visibility='gm';self.scene.save()
        with self.assertRaises(MapError):maps.layer_state(self.campaign.pk,self.player.pk,self.scene.pk)
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(MapError):tokens.command(self.campaign.pk,self.player.pk,'remove',{'mapId':str(self.scene.pk),'tokenIds':[str(self.token.pk)]},uuid.uuid4())
            self.assertFalse(send.called)
