"""Shader actions are bounded, scene-local, transactional and respect component owners."""
from copy import deepcopy
import uuid
from django.test import TestCase, override_settings
from gravewright.maps import services, blueprint_testing
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import Scene, SceneObject
from . import test_torches as fixtures
from .test_levers import node, execution


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],ALLOWED_HOSTS=['testserver'],GRAVEWRIGHT_MAP_TILER='pillow',DYNAMIC_LIGHTING_ENABLED=True)
class ShaderControlTests(TestCase):
    setUp=fixtures.TorchTests.setUp
    asset=fixtures.TorchTests.asset
    post=fixtures.TorchTests.post
    save=fixtures.TorchTests.save
    generate=fixtures.TorchTests.generate
    files=fixtures.TorchTests.files
    generated=fixtures.TorchTests.generated
    update_scene=fixtures.TorchTests.update_scene
    torch=fixtures.TorchTests.torch
    children=fixtures.TorchTests.children
    command=fixtures.TorchTests.command

    def graph(self, actions, *, target=None):
        blueprint=default_blueprint('torch')
        nodes=[node('event','event',event='interact')]
        nodes.extend(node('control'+str(i),'shaderControl',targetId=target or self.shader_id,property=key,value=value) for i,(key,value) in enumerate(actions))
        blueprint['graphs']['interact']={'nodes':nodes,'edges':[execution(a['id'],b['id']) for a,b in zip(nodes,nodes[1:])]}
        return blueprint

    def test_generated_bindings_change_parameters_and_keep_source_untouched(self):
        self.doc['decorations'][0]['blueprint']=self.graph([('enabled',True),('color','#12abcd'),('speed',2),('opacity',.3)])
        original=deepcopy(self.doc)
        self.generated()
        shader=self.children()['shaders'];source=shader.data['source']
        self.command()
        shader.refresh_from_db()
        self.assertEqual((shader.data['enabled'],shader.data['color'],shader.data['speed'],shader.data['opacity']),(True,'#12abcd',2,.3))
        self.assertEqual(shader.data['source'],source)
        self.assertEqual(self.doc,original)
        self.assertEqual(self.torch().data['blueprint']['graphs']['interact']['nodes'][1]['targetId'],str(shader.pk))
        self.update_scene()
        shader.refresh_from_db();self.assertEqual(shader.data['opacity'],.3)

    def test_flame_gate_keeps_enabled_intent_and_restores_it(self):
        self.doc['decorations'][0]['torch']['lit']=False
        self.doc['decorations'][0]['blueprint']=self.graph([('enabled',True),('intensity',.2)])
        self.generated();self.command()
        parent=self.torch();shader=self.children()['shaders']
        self.assertTrue(parent.data['torch']['components']['shaders']['enabled'])
        self.assertFalse(shader.data['enabled'])
        self.assertEqual(shader.data['intensity'],.2)
        self.command('torch-light',lit=True)
        shader.refresh_from_db();self.assertTrue(shader.data['enabled'])

    def test_independent_shader_is_controlled_without_changing_the_torch_component(self):
        independent=deepcopy(self.doc['shaders'][0]);independent.update(id=str(uuid.uuid4()),name='Independent',x=1,y=1)
        self.doc['shaders'].append(independent)
        self.doc['decorations'][0]['blueprint']=self.graph([('opacity',.15)],target=independent['id'])
        self.generated();self.command(user=self.player)
        self.assertEqual(self.scene.elements.get(kind='shaders',data__name='Independent').data['opacity'],.15)
        self.assertEqual(self.children()['shaders'].data['opacity'],1)

    def test_runtime_rejects_foreign_target_and_invalid_value_without_partial_writes(self):
        for property,value in [('source','void main(){}'),('speed',9),('opacity',-1),('enabled',1),('color','red')]:
            with self.subTest(property=property),self.assertRaises(services.MapError):
                clean_blueprint(self.graph([(property,value)]))
        self.doc['decorations'][0]['blueprint']=self.graph([('opacity',.4)])
        self.generated();parent=self.torch();shader=self.children()['shaders'];before=deepcopy(shader.data)
        foreign=SceneObject.objects.create(scene=Scene.objects.create(campaign=self.other,name='Foreign',width=100,height=100),kind='shaders',data=shader.data)
        raw=self.graph([('opacity',.8)],target=str(foreign.pk));parent.data['blueprint']=raw;parent.save()
        with self.assertRaises(services.MapError):self.command()
        shader.refresh_from_db();self.assertEqual(shader.data,before)

    def test_draft_rehearsal_applies_shader_delta_without_persistence(self):
        self.doc['decorations'][0]['blueprint']=self.graph([('color','#abcdef'),('opacity',.25)])
        count=SceneObject.objects.count()
        result=blueprint_testing.run_draft(self.campaign.pk,self.gm.pk,{'request_id':str(uuid.uuid4()),'document':self.doc,'elementId':self.torch_id,'event':'interact'})
        self.assertTrue(result['ok'],result)
        change=next(change for change in result['changes']['elements'] if change['sourceId']==self.shader_id)
        self.assertEqual(change['after']['data']['opacity'],.25)
        self.assertEqual(SceneObject.objects.count(),count)

    def test_invalid_connected_runtime_value_rolls_back_the_chain(self):
        raw=self.graph([('opacity',.4),('speed',1)])
        graph=raw['graphs']['interact']
        graph['nodes'].append(node('invalid','getVariable',scope='element',name='Speed',valueType='number',default=9))
        graph['edges'].append({'from':'invalid','output':'value','to':'control1','input':'value','kind':'data'})
        self.doc['decorations'][0]['blueprint']=raw
        self.generated();shader=self.children()['shaders'];before=deepcopy(shader.data)
        with self.assertRaises(services.MapError):self.command()
        shader.refresh_from_db();self.assertEqual(shader.data,before)

    def test_template_bindings_and_deleted_shader_continuations(self):
        from gravewright.maps import blueprint_templates
        raw=self.graph([('opacity',.4)])
        raw['graphs']['interact']['nodes'][1]['targetId']={'binding':'Shader'}
        definition={'version':1,'blueprint':raw,'bindings':[{'id':'Shader','type':'shader','label':'Mist'}],'parameters':[]}
        clean=blueprint_templates.clean_definition(definition)
        rebound=blueprint_templates.resolve_definition(clean,{'Shader':self.shader_id},owner_id=self.torch_id)
        graph=rebound['graphs']['interact'];graph['nodes'].append(node('on','state',targetState='on'));graph['edges'].append(execution('control0','on'))
        self.doc['decorations'][0]['blueprint']=rebound
        self.generated();shader=self.children()['shaders']
        services.command(self.campaign.pk,self.gm.pk,'objects',{'mapId':str(self.scene.pk),'area':'shaders','action':'delete','data':{'id':str(shader.pk)}},uuid.uuid4())
        self.command()
        self.assertEqual(self.torch().data['torch']['state'],'on')
        self.assertFalse(any(node['type']=='shaderControl' for node in self.torch().data['blueprint']['graphs']['interact']['nodes']))
