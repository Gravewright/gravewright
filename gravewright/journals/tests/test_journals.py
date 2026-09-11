from copy import deepcopy
from io import BytesIO
import tempfile
import uuid
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from channels.db import database_sync_to_async as db
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.campaigns.models import Membership
from gravewright.journals import services
from gravewright.journals.models import Journal, Folder


def doc(text, secret=False):
    return {'format':'gw-journal-doc-v1','version':1,'doc':{'type':'doc','content':[
        {'type':'paragraph','attrs':{'visibility':'gm' if secret else 'public'},'content':[{'type':'text','text':text}]}]}}


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
 CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}},
 GRAVEWRIGHT_HEARTBEAT_SECONDS=.1,GRAVEWRIGHT_PRESENCE_TTL=3,ALLOWED_HOSTS=['testserver'])
class JournalTests(TransactionTestCase):
    setUp=fixtures.SocketTests.setUp
    socket=fixtures.SocketTests.socket
    event=fixtures.SocketTests.event
    finish=fixtures.SocketTests.finish

    def command(self,action,data,user=None,request_id=None):
        return services.command(self.campaign.pk,(user or self.gm).pk,action,data,request_id or str(uuid.uuid4()))

    def create(self,user=None):
        return self.command('create',{'title':'Chronicle'},user)['journal_id']

    def payload(self,journal_id,user=None):
        j=Journal.objects.get(pk=journal_id)
        return {'journal_id':journal_id,'version':j.version,'title':j.title,'visibility':j.visibility,'data':deepcopy(j.data)}

    def test_private_documents_and_grants_and_conflicts(self):
        journal_id=self.create()
        self.assertEqual(services.state(self.campaign.pk,self.player.pk)['journals'],[])
        self.command('access',{'journal_id':journal_id,'target_user_id':str(self.player.pk),'access_level':'owner'})
        payload=self.payload(journal_id);payload['data']['content']=doc('Player text')
        self.command('update',payload,self.player)
        with self.assertRaises(services.JournalError) as error:self.command('update',payload,self.player)
        self.assertEqual(error.exception.code,'conflict')
        self.command('access',{'journal_id':journal_id,'target_user_id':str(self.player.pk),'access_level':'none'})
        self.assertEqual(services.state(self.campaign.pk,self.player.pk)['journals'],[])
        with self.assertRaises(services.JournalError):self.command('update',self.payload(journal_id),self.player)

    def test_secret_pages_and_nested_blocks_are_filtered_and_preserved(self):
        jid=self.create();payload=self.payload(jid);payload['visibility']='shared'
        payload['data']['content']=doc('Public')
        payload['data']['content']['doc']['content'].append({'type':'blockquote','content':doc('Nested secret',True)['doc']['content']})
        payload['data']['gm']={'notes':doc('GM only'),'secrets':doc('Hidden')}
        payload['data']['sections']=[{'id':'public','title':'Public page','kind':'text','audience':'public','content':doc('Visible')},{'id':'secret','title':'Secret page','kind':'text','audience':'gm','content':doc('Secret text')}]
        self.command('update',payload)
        self.command('access',{'journal_id':jid,'target_user_id':str(self.player.pk),'access_level':'owner'})
        view=services.state(self.campaign.pk,self.player.pk)['journals'][0]
        self.assertNotIn('secret',str(view).lower());self.assertNotIn('GM only',str(view))
        data={'content':doc('Edited'),'sections':view['editable_sections'],'gm':{'notes':doc('Forged')}}
        self.command('update',{'journal_id':jid,'version':view['version'],'title':'Edited','visibility':'shared','data':data},self.player)
        full=services.state(self.campaign.pk,self.gm.pk)['journals'][0]
        self.assertIn('Nested secret',str(full));self.assertIn('Secret page',str(full));self.assertIn('GM only',str(full));self.assertNotIn('Forged',str(full))

    def test_folder_moves_are_acyclic_and_delete_reparents_documents(self):
        parent=self.command('folder-create',{'name':'Parent'})['folder_id']
        child=self.command('folder-create',{'name':'Child','parent_id':parent})['folder_id']
        with self.assertRaises(services.JournalError):self.command('folder-move',{'folder_id':parent,'target_parent_id':child})
        jid=self.command('create',{'title':'Inside','folder_id':child})['journal_id']
        self.command('folder-delete',{'folder_id':child})
        self.assertEqual(str(Journal.objects.get(pk=jid).folder_id),parent)
        self.assertEqual(services.state(self.campaign.pk,self.player.pk)['folders'],[])
        with self.assertRaises(services.JournalError):services.command(self.other.pk,self.outsider.pk,'move',{'journal_id':jid},str(uuid.uuid4()))

    def test_retry_creates_only_one_document_and_sanitizes_links(self):
        request_id=str(uuid.uuid4());one=self.command('create',{'title':'Same'},request_id=request_id)
        two=self.command('create',{'title':'Same'},request_id=request_id)
        self.assertEqual(one,two);self.assertEqual(Journal.objects.count(),1)
        p=self.payload(one['journal_id']);p['data']['content']=doc('Click')
        p['data']['content']['doc']['content'][0]['content'][0]['marks']=[{'type':'link','attrs':{'href':'javascript:alert(1)'}}]
        self.command('update',p);self.assertNotIn('javascript:',str(Journal.objects.get(pk=one['journal_id']).data))

    def test_image_assets_enforce_page_visibility_and_journal_scope(self):
        with tempfile.TemporaryDirectory() as media,override_settings(MEDIA_ROOT=media):
            jid=self.create();self.client.force_login(self.gm)
            buffer=BytesIO();Image.new('RGB',(8,8),'red').save(buffer,format='PNG')
            response=self.client.post('/game/journal/asset',{'campaign_id':str(self.campaign.pk),'journal_id':jid,'file':SimpleUploadedFile('test.png',buffer.getvalue(),content_type='image/png')})
            self.assertEqual(response.status_code,200);asset=response.json()
            payload=self.payload(jid);payload['visibility']='shared';payload['data']['sections']=[{'id':'secret','title':'GM image','kind':'image','audience':'gm','assetId':asset['asset_id'],'src':asset['src']}]
            self.command('update',payload)
            self.client.force_login(self.player);self.assertEqual(self.client.get(asset['src']).status_code,404)
            other=self.create(self.player);p=self.payload(other);p['data']['sections']=[{'id':'stolen','kind':'image','assetId':asset['asset_id']}]
            with self.assertRaises(services.JournalError):self.command('update',p,self.player)
            self.client.force_login(self.gm);response=self.client.get(asset['src']);self.assertEqual(response.status_code,200);response.close()

    async def test_websocket_updates_are_filtered_per_member(self):
        gm,player=self.socket(self.gm),self.socket(self.player)
        try:
            for socket in [gm,player]:
                self.assertTrue((await socket.connect())[0]);await self.event(socket,'chat.history')
                await socket.send_json_to({'type':'journals.sync'});await self.event(socket,'journals.state')
            await gm.send_json_to({'type':'journals.command','payload':{'action':'create','data':{'title':'Secret chronicle'},'requestId':str(uuid.uuid4())}})
            ack=await self.event(gm,'journals.ack');jid=ack['result']['journal_id']
            self.assertEqual((await self.event(player,'journals.state'))['journals'],[])
            payload=await db(self.payload)(jid);payload['visibility']='shared'
            await gm.send_json_to({'type':'journals.command','payload':{'action':'update','data':payload,'requestId':str(uuid.uuid4())}})
            await self.event(gm,'journals.ack')
            self.assertEqual((await self.event(player,'journals.state'))['journals'][0]['title'],'Secret chronicle')
        finally:await self.finish()
