/* Core-owned semantic input dispatcher. Raw browser events never reach packages. */
(() => {
    const commands=new Map(), gestures=new Map(), pointers=new Map(), bindings=new Map();
    const normalize=(event)=>[event.ctrlKey&&"Ctrl",event.altKey&&"Alt",event.shiftKey&&"Shift",event.metaKey&&"Meta",event.key.length===1?event.key.toUpperCase():event.key].filter(Boolean).join("+");
    const typing=()=>{const node=document.activeElement;return Boolean(node&&(node.matches?.("input, textarea, select")||node.isContentEditable));};
    function registerCommand(packageId, definition, invoke) { const key=`${packageId}:${definition.id}`;commands.set(key,{packageId,definition,invoke});return()=>commands.delete(key); }
    function updateBinding(packageId,commandId,binding){bindings.set(`${packageId}:${commandId}`,binding);}
    function registerGesture(packageId,definition,invoke){const key=`${packageId}:${definition.id}`;gestures.set(key,{packageId,definition,invoke});return()=>gestures.delete(key);}
    addEventListener("keydown",event=>{
        if(event.key==="Escape"){pointers.clear();return;}
        if(event.repeat)return;
        const binding=normalize(event);
        for(const entry of commands.values()){
            const contexts=entry.definition.contexts||["global"];
            if(typing()&&(contexts.includes("text-input-excluded")||!contexts.includes("text-input")))continue;
            const resolved=bindings.get(`${entry.packageId}:${entry.definition.id}`);
            if(resolved ? resolved!==binding : !(entry.definition.defaultBindings||[]).includes(binding))continue;
            event.preventDefault();void entry.invoke({commandId:entry.definition.id,packageId:entry.packageId,source:"binding",binding,context:contexts.includes("scene")?"scene":"global"});break;
        }
    },true);
    addEventListener("pointerdown",event=>{pointers.set(event.pointerId,{x:event.clientX,y:event.clientY,t:performance.now(),type:event.pointerType,moved:false});},true);
    addEventListener("pointermove",event=>{const p=pointers.get(event.pointerId);if(p&&Math.hypot(event.clientX-p.x,event.clientY-p.y)>8)p.moved=true;},true);
    addEventListener("pointercancel",event=>{pointers.delete(event.pointerId);},true);
    addEventListener("pointerup",event=>{
        const p=pointers.get(event.pointerId);pointers.delete(event.pointerId);if(!p)return;
        const elapsed=performance.now()-p.t;const semantic=p.moved?"drag":elapsed>=500?"long-press":"tap";
        // A second live pointer cancels specialized tool gestures deterministically.
        if(pointers.size)return;
        for(const entry of gestures.values())if(entry.definition.gesture===semantic)void entry.invoke({commandId:entry.definition.commandId,packageId:entry.packageId,source:"gesture",gesture:semantic,pointerType:["mouse","touch","pen"].includes(p.type)?p.type:"mouse"});
    },true);
    try { const context=JSON.parse(document.getElementById("gravewright-game-context")?.textContent||"{}"); for(const row of context.inputBindings||[]) updateBinding(row.package_id,row.command_id,row.binding); } catch { /* fail closed */ }
    window.GravewrightInputRuntime=Object.freeze({registerCommand,registerGesture,updateBinding});
})();
