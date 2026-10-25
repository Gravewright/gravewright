import { clone, objectKinds, wallSegments } from './model.js';
import { regionContainsPoint, regionMatchesFilters } from './region-model.js';

export function playerWalls(document) {
    const visible=new Set(document.layers.filter(layer=>layer.visible).map(layer=>layer.id));
    const geometry={...document,doors:document.doors.filter(item=>visible.has(item.layerId))};
    const native=(item,kind)=>({kind,...item,door_state:item.state,
        movement_behavior:item.behavior?.movement||'block',vision_behavior:item.behavior?.vision||'block',
        vertical_bottom:item.vertical?.bottom??null,vertical_top:item.vertical?.top??null});
    return [...document.walls.filter(item=>visible.has(item.layerId)).flatMap(item=>wallSegments(geometry,item).map(segment=>({...native(item,'wall'),...segment}))),
        ...geometry.doors.map(item=>native(item,'door'))];
}

export function playerDocument(source) {
    const doc=clone(source),visible=new Set(doc.layers.filter(layer=>layer.visible).map(layer=>layer.id));
    for(const kind of objectKinds)doc[kind]=(doc[kind]||[]).filter(item=>visible.has(item.layerId)&&!item.testHidden);
    return doc;
}

export function areaEvents(document, from, to, token = {disposition:'neutral',hidden:false}) {
    const events=[],visible=new Set(document.layers.filter(layer=>layer.visible).map(layer=>layer.id));
    const areas=[...document.decorations.filter(item=>Number.isFinite(item.presenceRadius)).map(item=>({item,contains:point=>Math.hypot(point.x-item.x-item.width/2,point.y-item.y-item.height/2)<=item.presenceRadius})),
        ...document.regions.filter(item=>item.enabled!==false&&regionMatchesFilters(item.filters,token)).map(item=>({item,contains:point=>regionContainsPoint(item,point)}))].filter(({item})=>visible.has(item.layerId));
    const dx=to.x-from.x,dy=to.y-from.y;
    const at=progress=>({x:from.x+dx*progress,y:from.y+dy*progress});
    for(const {item,contains}of areas){
        const cuts=[0,1];
        if(Number.isFinite(item.presenceRadius)){
            const x=from.x-item.x-item.width/2,y=from.y-item.y-item.height/2,a=dx*dx+dy*dy,b=2*(x*dx+y*dy),c=x*x+y*y-item.presenceRadius**2;
            const discriminant=b*b-4*a*c;
            if(a&&discriminant>0)cuts.push((-b-Math.sqrt(discriminant))/(2*a),(-b+Math.sqrt(discriminant))/(2*a));
        }else{
            if(dx)cuts.push((item.x-from.x)/dx,(item.x+item.width-from.x)/dx);
            if(dy)cuts.push((item.y-from.y)/dy,(item.y+item.height-from.y)/dy);
        }
        const points=[...new Set(cuts.filter(value=>value>=0&&value<=1))].sort((a,b)=>a-b);
        let inside=contains(from);
        for(let i=0;i<points.length;i++){
            const progress=points[i],next=contains(at(i===points.length-1?progress:(progress+points[i+1])/2));
            if(next!==inside){events.push({id:item.id,event:next?'presence:enter':'presence:exit',point:at(progress),progress});inside=next;}
        }
    }
    return events.sort((a,b)=>a.progress-b.progress);
}

export function authoredTestDocument(source) {
    const doc=clone(source);
    for(const kind of objectKinds)for(const item of doc[kind]||[])for(const key of ['testAppearance','testHidden','testNative','testTransform','testRegion'])delete item[key];
    return doc;
}
