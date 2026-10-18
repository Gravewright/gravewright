"""Scene-zone geometry and audience rules ported from the original engine."""
import math
from .models import SceneObject
from .objects import number, boolean, choice, entry, get_object
from .services import MapError, manage
from gravewright.campaigns.models import Membership


class Geometry:
    MAX_VERTICES=256
    @classmethod
    def _normalize_geometry(cls,g):
        if not isinstance(g,dict) or g.get("shape") not in {"circle","rect","polygon"}: raise ValueError
        shape=g["shape"]
        def number(v):
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1_000_000: raise ValueError
            return float(v)
        if shape=="circle":
            x,y,r=number(g.get("x")),number(g.get("y")),number(g.get("radius"))
            if r<=0: raise ValueError
            return {"shape":shape,"x":x,"y":y,"radius":r},(x-r,y-r,x+r,y+r)
        if shape=="rect":
            x,y,w,h=number(g.get("x")),number(g.get("y")),number(g.get("width")),number(g.get("height"))
            if w<=0 or h<=0: raise ValueError
            return {"shape":shape,"x":x,"y":y,"width":w,"height":h},(x,y,x+w,y+h)
        pts=g.get("points")
        if not isinstance(pts,list) or not 3<=len(pts)<=cls.MAX_VERTICES: raise ValueError
        points=[{"x":number(p.get("x")),"y":number(p.get("y"))} for p in pts if isinstance(p,dict)]
        if len(points)!=len(pts): raise ValueError
        # Reject zero-area polygons; self-intersection is deliberately rejected.
        area=sum(points[i]["x"]*points[(i+1)%len(points)]["y"]-points[(i+1)%len(points)]["x"]*points[i]["y"] for i in range(len(points)))
        if abs(area)<1e-9 or cls._self_intersects(points): raise ValueError
        xs=[p["x"] for p in points]; ys=[p["y"] for p in points]
        return {"shape":shape,"points":points},(min(xs),min(ys),max(xs),max(ys))
    @staticmethod
    def _self_intersects(p):
        def orient(a,b,c): return (b["x"]-a["x"])*(c["y"]-a["y"])-(b["y"]-a["y"])*(c["x"]-a["x"])
        n=len(p)
        for i in range(n):
            for j in range(i+1,n):
                if i==j or (i+1)%n==j or i==(j+1)%n: continue
                a,b,c,d=p[i],p[(i+1)%n],p[j],p[(j+1)%n]
                if orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0: return True
        return False
    @staticmethod
    def contains(z,x,y,elevation):
        if z["vertical_bottom"] is not None and elevation<z["vertical_bottom"] or z["vertical_top"] is not None and elevation>z["vertical_top"]: return False
        g=z["geometry"]
        if g["shape"]=="circle": return (x-g["x"])**2+(y-g["y"])**2<=g["radius"]**2
        if g["shape"]=="rect": return g["x"]<=x<=g["x"]+g["width"] and g["y"]<=y<=g["y"]+g["height"]
        inside=False; pts=g["points"]; j=len(pts)-1
        for i,p in enumerate(pts):
            q=pts[j]
            if (p["y"]>y)!=(q["y"]>y) and x < (q["x"]-p["x"])*(y-p["y"])/(q["y"]-p["y"])+p["x"]: inside=not inside
            j=i
        return inside
    @classmethod
    def crosses(cls,z,a,b,elevation):
        if cls.contains(z,a[0],a[1],elevation) or cls.contains(z,b[0],b[1],elevation): return False
        g=z["geometry"]
        if g["shape"]=="circle":
            dx=b[0]-a[0]; dy=b[1]-a[1]; length=dx*dx+dy*dy
            if length==0:return False
            t=max(0,min(1,((g["x"]-a[0])*dx+(g["y"]-a[1])*dy)/length)); x=a[0]+t*dx; y=a[1]+t*dy
            return (x-g["x"])**2+(y-g["y"])**2<=g["radius"]**2
        pts=([{"x":g["x"],"y":g["y"]},{"x":g["x"]+g["width"],"y":g["y"]},{"x":g["x"]+g["width"],"y":g["y"]+g["height"]},{"x":g["x"],"y":g["y"]+g["height"]}] if g["shape"]=="rect" else g["points"])
        def side(p,q,r): return (q["x"]-p["x"])*(r[1]-p["y"])-(q["y"]-p["y"])*(r[0]-p["x"])
        def intersects(p,q):
            # Collinear segments intersect only when their finite bounds overlap.
            if (max(a[0],b[0]) < min(p["x"],q["x"]) or min(a[0],b[0]) > max(p["x"],q["x"])
                    or max(a[1],b[1]) < min(p["y"],q["y"]) or min(a[1],b[1]) > max(p["y"],q["y"])):
                return False
            start,end={"x":a[0],"y":a[1]},{"x":b[0],"y":b[1]}
            return (side(p,q,a)*side(p,q,b)<=0
                    and side(start,end,(p["x"],p["y"]))*side(start,end,(q["x"],q["y"]))<=0)
        return any(intersects(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts)))


def visible(data,who):
    audience=data['audience']
    return who.role=='gm' or audience['kind']=='campaign' or audience['kind']=='users' and str(who.user_id) in audience.get('ids',[])


def clean(raw,who,previous=None, *, scene_id=None):
    if not isinstance(raw,dict):raise MapError('Invalid zone.')
    data={**(previous or {}),**raw}
    try:geometry,_=Geometry._normalize_geometry(data.get('geometry'))
    except (ValueError,TypeError,KeyError):raise MapError('Invalid zone geometry.') from None
    audience=data.get('audience',{'kind':'campaign'})
    if not isinstance(audience,dict):raise MapError('Invalid zone audience.')
    kind=choice(audience.get('kind'),{'campaign','gm','users'})
    ids=audience.get('ids',[]) if kind=='users' else []
    members={str(i) for i in Membership.objects.filter(campaign_id=who.campaign_id).values_list('user_id',flat=True)}
    if not isinstance(ids,list) or len(ids)>64 or any(not isinstance(i,str) or i not in members for i in ids):raise MapError('Invalid zone audience.')
    vertical=data.get('vertical') or {}
    if not isinstance(vertical,dict):raise MapError('Invalid zone elevation.')
    bottom=vertical.get('bottom');top=vertical.get('top')
    if bottom is not None:bottom=number(bottom)
    if top is not None:top=number(top)
    if bottom is not None and top is not None and bottom>top:raise MapError('Invalid zone elevation.')
    tags=data.get('tags',[])
    if not isinstance(tags,list) or len(tags)>32 or any(not isinstance(t,str) or len(t)>64 for t in tags):raise MapError('Invalid zone tags.')
    result = dict(geometry=geometry,type=str(data.get('type') or 'standard')[:64],
        audience={'kind':kind,**({'ids':list(dict.fromkeys(ids))} if ids else {})},
        vertical={'bottom':bottom,'top':top},enabled=boolean(data.get('enabled',True)),tags=list(dict.fromkeys(tags)),
        packageProvenance=(previous or {}).get('packageProvenance',{'packageId':'core','providerId':None}))
    if 'region' in data:
        region = data['region']
        authored = raw.get('region', {})
        if isinstance(region, dict):
            region = {**(previous or {}).get('region', {}), **region}
        if (not isinstance(region, dict) or not isinstance(authored, dict) or set(authored) - {'name', 'filters'}
                or not isinstance(region.get('name'), str) or not region['name'].strip()
                or len(region['name']) > 120 or '\x00' in region['name'] or geometry['shape'] != 'rect'):
            raise MapError('Invalid presence region.')
        result['audience'] = {'kind': 'gm'}
        result['region'] = {'name': region['name'].strip(), 'state': 'empty', 'occupants': []}
        if previous and 'arrivalGates' in previous.get('region', {}):
            from copy import deepcopy
            result['region']['arrivalGates'] = deepcopy(previous['region']['arrivalGates'])
        # Authored settings are patched independently of the private occupancy ledger.
        filters = authored.get('filters', (previous or {}).get('region', {}).get('filters'))
        if filters is not None:
            from .regions import clean_filters
            result['region']['filters'] = clean_filters(filters, campaign_id=who.campaign_id, scene_id=scene_id)
        elif 'filters' in authored:
            raise MapError('Invalid region filters.')
        if data.get('blueprint') is not None:
            from .blueprint_runtime import clean_native_blueprint
            result['blueprint'] = clean_native_blueprint(data['blueprint'], who.campaign_id, scene_id, kind='region')
    elif 'blueprint' in raw:
        raise MapError('Only presence regions can have a blueprint.')
    from .blueprint_variables import copy_runtime
    return copy_runtime(previous, result)


def apply(scene,who,action,p):
    manage(who)
    if action=='create':
        if scene.elements.count()>=5000:raise MapError('Scene object limit reached.')
        data = clean(p,who,scene_id=scene.pk)
        if 'region' in data:
            from .regions import MAX_REGIONS, presence_rows
            if len(presence_rows(scene)) >= MAX_REGIONS:
                raise MapError('The scene has too many presence regions.')
        obj=SceneObject(scene=scene,kind='zones',data=data)
    elif action in ('update','delete'):
        obj=get_object(scene,p.get('zone_id',p.get('id')),'zones')
        version=p.get('expected_version',p.get('version'))
        if type(version) is not int or obj.version!=version:raise MapError('This zone changed. Refresh before editing.','conflict')
        if action=='delete':
            from .blueprint_lifecycle import destroy_objects
            rid=str(obj.pk);destroy_objects(scene,who,[obj]);return {'id':rid,'deleted':True}
        was_region = 'region' in obj.data
        obj.data=clean(p.get('patch',{}),who,obj.data,scene_id=scene.pk);obj.version+=1
        if not was_region and 'region' in obj.data:
            from .regions import MAX_REGIONS, presence_rows
            if len(presence_rows(scene)) >= MAX_REGIONS:
                raise MapError('The scene has too many presence regions.')
    else:raise MapError('Unknown zone command.')
    if 'region' in obj.data:
        from .regions import baseline, projection
        baseline(scene, [obj])
        obj.save()
        return {**projection(entry(obj)), 'sceneId':str(scene.pk)}
    obj.save()
    return {**entry(obj),'sceneId':str(scene.pk)}


def movement_events(scene, token, before, *, teleport=False):
    """Emit enter/leave/cross events only after the authoritative move commits."""
    from django.db import transaction
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from gravewright.tokens.services import geometry, presentation
    cell,ox,oy,_,_=geometry(scene)
    size=presentation(token)['token']['size']
    start=(ox+(before[0]+size/2)*cell,oy+(before[1]+size/2)*cell)
    end=(ox+(token.grid_x+size/2)*cell,oy+(token.grid_y+size/2)*cell)
    for obj in scene.elements.filter(kind='zones'):
        # Pressure plates use private Blueprint diagnostics, not legacy signals.
        if 'region' in obj.data:continue
        if not obj.data['enabled']:continue
        zone={**obj.data,'vertical_bottom':obj.data['vertical']['bottom'],'vertical_top':obj.data['vertical']['top']}
        was=Geometry.contains(zone,*start,before[2]);now=Geometry.contains(zone,*end,token.elevation)
        within=(zone['vertical_bottom'] is None or token.elevation>=zone['vertical_bottom']) and (zone['vertical_top'] is None or token.elevation<=zone['vertical_top'])
        crossing=not teleport and within and not was and not now and Geometry.crosses(zone,start,end,token.elevation)
        event='zone.entered' if not was and now else 'zone.left' if was and not now else 'zone.crossed' if crossing else None
        if not event:continue
        payload={'type':'room.zone','event':event,'sceneId':str(scene.pk),'zoneId':str(obj.pk),'tokenId':str(token.pk),'schema_version':1}
        transaction.on_commit(lambda p=payload:async_to_sync(get_channel_layer().group_send)(f'table.{scene.campaign_id.hex}',p))
