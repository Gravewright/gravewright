/* User-specific scene projection. Authority and destination are server-owned. */
(() => {
    let transitioning=false;
    document.addEventListener("vtt:transport-event",event=>{
        const {event:name,payload}=event.detail||{};
        if(name!=="navigation.scene.changed"||!payload?.scene_id||transitioning)return;
        const context=JSON.parse(document.getElementById("gravewright-game-context")?.textContent||"{}");
        if(context.scene?.id===payload.scene_id)return;
        transitioning=true;
        // Reload enters the normal Gravewright scene bootstrap; packages never touch routing.
        window.location.reload();
    });
})();
