"""Isolated, deliberately busy scene for repeatable in-game measurements."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
script = root / 'tests/e2e/ownership_server.py'
source = script.read_text(encoding='utf-8')
source = source.replace("width=800,height=600", "width=2400,height=1600")
source = source.replace("token=Token.objects.create(scene=scene,actor=actor)", """
token=Token.objects.create(scene=scene,actor=actor,grid_x=2,grid_y=2)
from gravewright.maps.models import MapAsset, SceneObject
from django.core.files.base import ContentFile
from PIL import Image
import io
raw=io.BytesIO();Image.new('RGBA',(160,100),(195,150,70,255)).save(raw,format='PNG')
asset=MapAsset(campaign=campaign,name='Performance image',width=160,height=100)
asset.file.save('performance.png',ContentFile(raw.getvalue()))
SceneObject.objects.bulk_create([SceneObject(scene=scene,kind='images',data={
 'asset_id':str(asset.pk),'src':f'/game/map-assets/{asset.pk}','natural_width':160,'natural_height':100,
 'x':200+(i%10)*210,'y':300+(i//10)*200,'scale':1,'rotation':0,'layer':'map','z_index':i
}) for i in range(60)])
for i in range(60):
 data=normalize({});data['performance_fixture']='x'*100000
 row=Actor.objects.create(campaign=campaign,name=f'Performance hero {i}',data=data,permissions={'default':'read'})
 if i<30:Token.objects.create(scene=scene,actor=row,grid_x=3+i%10*2,grid_y=1+i//10*2)
for i in range(80):
 Journal.objects.create(campaign=campaign,title=f'Performance diary {i}',visibility='shared',
  data=normalize_diary_data({'sections':[{'id':f'page-{n}','title':f'Page {n}','kind':'text'} for n in range(5)]}))
""")
source = source.replace("'sessions':sessions", "'sessions':sessions,'database':str(settings.DATABASES['default']['NAME'])")
exec(compile(source, str(script), 'exec'), {'__file__': str(script), '__name__': '__main__'})
