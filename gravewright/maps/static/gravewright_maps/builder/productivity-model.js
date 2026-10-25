/** Atomic editing helpers; scene state and authored identities remain untouched on failure. */
import { clone, objectKinds, selectionBounds, translateSelection, rotateSelection, fitsBounds, doorFits, documentBounds } from './model.js';
import { expandTorchSelection, torchOwner } from './torch-model.js';
import { moveSelectionToLayer } from './layer-model.js';

export function organizeSelection(document, refs, action, angle = 90) {
    const next = clone(document);
    const parents = new Set(refs.filter(ref => ref.kind === 'decorations').map(ref => ref.id));
    const roots = refs.filter(ref => !parents.has(torchOwner(next, ref.kind, ref.id)?.id));
    const bounds = selectionBounds(next, roots);
    if (!bounds || !roots.length) return null;
    if (action === 'rotate') return rotateSelection(next, roots, angle) ? next : null;
    if (roots.length < 2) return null;
    const vertical = ['top', 'middle', 'bottom', 'distribute-y'].includes(action);
    const axis = vertical ? 'y' : 'x', dimension = vertical ? 'height' : 'width';
    const entries = roots.map(ref => ({ref, box:selectionBounds(next, [ref])})).sort((a,b) => a.box[axis]-b.box[axis]);
    const distribute = action.startsWith('distribute-');
    if (distribute && entries.length < 3) return null;
    if (!['left','center','right','top','middle','bottom','distribute-x','distribute-y'].includes(action)) return null;
    const gap = distribute ? (bounds[dimension] - entries.reduce((sum,entry) => sum+entry.box[dimension],0))/(entries.length-1) : 0;
    let cursor = bounds[axis], changed = false;
    for (const {ref,box} of entries) {
        const target = distribute ? cursor : bounds[axis] + (['center','middle'].includes(action)
            ? (bounds[dimension]-box[dimension])/2 : ['right','bottom'].includes(action) ? bounds[dimension]-box[dimension] : 0);
        cursor += box[dimension]+gap;
        const delta = target-box[axis];
        if (Math.abs(delta) < .000001) continue;
        if (!translateSelection(next,[ref],vertical?0:delta,vertical?delta:0)) return null;
        changed = true;
    }
    return changed ? next : null;
}

export function groupSelection(document, refs, name) {
    if (!refs.length || document.layers.length >= 32 || !name.trim() || name.trim().length > 80) return null;
    const next = clone(document), layer = {id:crypto.randomUUID(),name:name.trim(),visible:true,locked:false};
    next.layers.push(layer);
    return moveSelectionToLayer(next,refs,layer.id) ? {document:next,layerId:layer.id} : null;
}

export function selectionBundle(document, refs) {
    const ids = new Set(expandTorchSelection(document,refs).map(ref=>ref.id));
    if (!ids.size || ids.size > 100) throw new Error('Select up to 100 objects.');
    const bundle = clone(document);
    delete bundle.backgroundImage; delete bundle.sceneGeometry;
    for (const kind of objectKinds) bundle[kind]=(bundle[kind]||[]).filter(item=>ids.has(item.id));
    const available=new Set(bundle.assets.map(asset=>asset.assetId)),used=new Set();
    const collect=value=>{if(typeof value==='string'&&available.has(value))used.add(value);
        else if(value&&typeof value==='object')for(const child of Object.values(value))collect(child);};
    for(const kind of objectKinds)collect(bundle[kind]);
    bundle.assets=bundle.assets.filter(asset=>used.has(asset.assetId));
    const layers = new Set(objectKinds.flatMap(kind=>bundle[kind].map(item=>item.layerId)));
    bundle.layers = bundle.layers.filter(layer=>layers.has(layer.id)).map(layer=>({...layer,visible:true,locked:false}));
    return bundle;
}

export function placeBundle(document, bundle, point, layerId, maxObjects = 2000) {
    const layer = document.layers.find(layer=>layer.id===layerId);
    const refs = objectKinds.flatMap(kind=>(bundle[kind]||[]).map(item=>({kind,id:item.id})));
    const bounds = selectionBounds(bundle,refs);
    if (!bounds || !layer?.visible || layer.locked || objectKinds.reduce((n,kind)=>n+(document[kind]?.length||0),0)+refs.length>maxObjects) return null;
    const next = clone(document), mapping = new Map(refs.map(ref=>[ref.id,crypto.randomUUID()])), copies=[];
    const dx=point.x-bounds.x, dy=point.y-bounds.y;
    for (const kind of objectKinds) for (const source of bundle[kind]||[]) {
        const item=clone(source);item.id=mapping.get(source.id);item.layerId=layerId;
        if (kind==='walls'||kind==='doors') {item.x1+=dx;item.x2+=dx;item.y1+=dy;item.y2+=dy;}
        else {item.x+=dx;item.y+=dy;}
        if(item.torch) for(const field of ['lightId','particleId','shaderId']) if(mapping.has(item.torch[field]))item.torch[field]=mapping.get(item.torch[field]);
        for(const graph of Object.values(item.blueprint?.graphs||{}))for(const node of graph.nodes){
            if(mapping.has(node.targetId))node.targetId=mapping.get(node.targetId);
            if(node.targetIds)node.targetIds=node.targetIds.map(id=>mapping.get(id)||id);
        }
        (next[kind]||=[]).push(item);copies.push({kind,id:item.id});
    }
    const assets = new Set(next.assets.map(asset=>asset.assetId));
    for(const asset of bundle.assets){
        if(next.assets.some(existing=>existing.assetId===asset.assetId&&existing.role!==asset.role))return null;
        if(!assets.has(asset.assetId)){next.assets.push(clone(asset));assets.add(asset.assetId);}
    }
    if(next.assets.length>256 || next.regions.length>128 || !fitsBounds(next) || !next.doors.every(item=>doorFits(next,item)))return null;
    return {document:next,refs:copies};
}

/** Spacing samples follow the whole stroke, including sparse pointer events. */
export function objectBrushSamples(previous, point, spacing, carry = 0) {
    const distance=Math.hypot(point.x-previous.x,point.y-previous.y), samples=[];
    if(!Number.isFinite(spacing)||spacing<.1||!Number.isFinite(distance))return {samples,carry};
    for(let length=spacing-carry;length<=distance && samples.length<2000;length+=spacing){
        samples.push({x:previous.x+(point.x-previous.x)*length/distance,y:previous.y+(point.y-previous.y)*length/distance});
    }
    return {samples,carry:(carry+distance)%spacing};
}

export function scatterObject(document, point, {assetId,width=1,height=1,rotation=0,scaleVariation=0,rotationVariation=0,layerId}, random=Math.random) {
    if(!assetId)return null;
    const factor=1+(random()*2-1)*Math.max(0,Math.min(.9,scaleVariation)), size=documentBounds(document);
    const w=Math.max(.05,Math.min(100,width*factor)),h=Math.max(.05,Math.min(100,height*factor));
    const item={id:crypto.randomUUID(),assetId,layerId,x:point.x-w/2,y:point.y-h/2,width:w,height:h,rotation:(rotation+(random()*2-1)*rotationVariation+720)%360};
    if(item.x<0||item.y<0||item.x+w>size.width||item.y+h>size.height)return null;
    return fitsBounds({...document,decorations:[item]})?item:null;
}
