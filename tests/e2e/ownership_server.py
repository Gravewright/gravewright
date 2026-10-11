"""Start an isolated fixture server for tests/e2e/ownership.py (port 30002)."""
import json,os,secrets,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
fixture_dir=root/'data'/'permissions-review'/secrets.token_hex(8)
fixture_dir.mkdir(parents=True)
settings.DATABASES['default']['NAME']=fixture_dir/'review.sqlite3'
settings.ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']
settings.DEBUG=True
settings.MEDIA_ROOT=fixture_dir/'media'
settings.PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
from django.core.management import call_command
call_command('migrate',verbosity=0,interactive=False)
from django.test import Client
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign,Membership
from gravewright.actors.models import Actor,Folder
from gravewright.items.models import Item
from gravewright.journals.models import Journal
from gravewright.journals.data import normalize_diary_data,empty_data_for
from gravewright.pdf_system.schema import normalize
from gravewright.cards.models import Deck,Card
from gravewright.maps.models import Scene,Broadcast
from gravewright.tokens.models import Token
from gravewright.compendiums.models import Pack
users=[];sessions=[]
for name,role in [('GM','owner'),('Alice','participant'),('Bruno','participant')]:
 user=User.objects.create_user(f'{secrets.token_hex(8)}@ownership.test',secrets.token_urlsafe(20),name=name,role=role);users.append(user)
 client=Client();client.force_login(user);sessions.append({'name':settings.SESSION_COOKIE_NAME,'value':client.cookies[settings.SESSION_COOKIE_NAME].value})
campaign=Campaign.objects.create(owner=users[0],name='Permissions browser review')
for user,role in zip(users,['gm','player','player']):Membership.objects.create(campaign=campaign,user=user,role=role)
folder=Folder.objects.create(campaign=campaign,name='Party')
actor=Actor.objects.create(campaign=campaign,folder=folder,name='Ownership hero',data=normalize({}),permissions={'default':'read'})
item=Item.objects.create(campaign=campaign,name='Ownership item',type='gear',system_id=campaign.system,permissions={'default':'read'})
journal=Journal.objects.create(campaign=campaign,title='Ownership journal',visibility='shared',data=normalize_diary_data({'sections':[{'id':'page','title':'Ownership page','kind':'text'}]}))
for kind,title in [('quest','Ownership quest'),('quest_board','Ownership quest board'),('roll_table','Ownership roll table')]:
 Journal.objects.create(campaign=campaign,title=title,type=kind,visibility='shared',data=empty_data_for(kind))
Journal.objects.create(campaign=campaign,title='Presentation book',data=normalize_diary_data({'sections':[
 {'id':'first','title':'First public page','kind':'text'},
 {'id':'second','title':'Second public page','kind':'text'},
 {'id':'secret','title':'GM secret page','kind':'text','audience':'gm'}]}))
scene=Scene.objects.create(campaign=campaign,name='Ownership scene',width=800,height=600)
Broadcast.objects.create(campaign=campaign,scene=scene)
token=Token.objects.create(scene=scene,actor=actor)
deck=Deck.objects.create(campaign=campaign,name='Ownership deck');Card.objects.create(deck=deck,name='Ace')
pack=Pack.objects.create(campaign=campaign,name='Ownership pack')
(root/'data'/'permissions-review-seed.json').write_text(json.dumps({'campaign':str(campaign.pk),'actor':str(actor.pk),'item':str(item.pk),'journal':str(journal.pk),'folder':str(folder.pk),'scene':str(scene.pk),'token':str(token.pk),'deck':str(deck.pk),'pack':str(pack.pk),'users':[str(u.pk) for u in users],'sessions':sessions}))
print('Permission review server ready on http://127.0.0.1:30002',flush=True)
call_command('runserver','127.0.0.1:30002',use_reloader=False,verbosity=0)
