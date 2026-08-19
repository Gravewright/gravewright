/* First-class core audio projection. Browser primitives never cross the SDK boundary. */
(() => {
    const instances = new Map();
    const pending = new Set();
    const transitions = new Map();
    const projections = new Map();
    let unlocked = false;
    const storedPreference = (channel) => {
        const value = Number(localStorage.getItem(`gravewright.audio.volume.${channel}`) ?? 1);
        return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 1;
    };
    const preference = (channel) => channel === "master"
        ? storedPreference(channel)
        : Math.min(storedPreference(channel), storedPreference("master"));
    const assetUrl = (asset) => asset?.kind === "package-asset"
        ? `/sdk/packages/${encodeURIComponent(asset.ownerPackageId || "")}/asset/${asset.id.split("/").map(encodeURIComponent).join("/")}`
        : `/game/sounds/assets/${encodeURIComponent(asset?.id || "")}/stream`;
    const master=()=>preference("master"), muted=()=>localStorage.getItem("gravewright.audio.muted")==="1";
    const effective=(logical,channel,id)=>Math.max(0,Math.min(1,logical))*Math.min(preference(channel),master())*(muted()?0:1)*(projections.get(id)??1);
    const isNativeSpatial=playback=>playback?.ownerPackageId==="core.sound"&&playback?.channel==="sfx"&&Boolean(playback?.sceneId);
    const seekToTimeline=(audio,playback)=>{const elapsed=Math.max(0,Date.now()/1000-Number(playback.startedAt||Date.now()/1000));if(Number.isFinite(audio.duration)&&audio.duration>0)audio.currentTime=playback.loop?elapsed%audio.duration:Math.min(elapsed,Math.max(0,audio.duration-.05));};
    const cancelTransition=(id)=>{const prior=transitions.get(id);if(prior)cancelAnimationFrame(prior.frame);transitions.delete(id);};
    function fade(audio,playback){
        cancelTransition(playback.id);
        const spec=playback.fade;if(!spec||!Number(spec.durationMs)){audio.volume=effective(playback.gain,playback.channel,playback.id);return;}
        const now=Date.now(),started=Number(spec.startedAt||playback.updatedAt||playback.startedAt*1000||now);
        const duration=Math.max(0,Number(spec.durationMs));const from=Number.isFinite(Number(spec.fromGain))?Number(spec.fromGain):(spec.direction==="out"?Number(playback.gain):0);
        const to=spec.direction==="out"?0:Number(playback.gain);const state={from,to,started,duration,effectiveGain:from,frame:0};
        const tick=()=>{const ratio=Math.max(0,Math.min(1,(Date.now()-started)/duration));const eased=spec.curve==="ease-in"?ratio*ratio:spec.curve==="ease-out"?1-(1-ratio)*(1-ratio):ratio;state.effectiveGain=from+(to-from)*eased;audio.volume=effective(state.effectiveGain,playback.channel,playback.id);if(ratio<1){state.frame=requestAnimationFrame(tick);}else{transitions.delete(playback.id);if(spec.direction==="out"){audio.pause();instances.delete(playback.id);}}};
        transitions.set(playback.id,state);tick();
    }
    async function project(playback) {
        if (!playback?.id) return;
        if(isNativeSpatial(playback)&&!projections.has(playback.id))projections.set(playback.id,0);
        let audio = instances.get(playback.id);
        if (playback.state === "stopped") { cancelTransition(playback.id); if (audio) { audio.pause(); instances.delete(playback.id); } pending.delete(playback.id); return; }
        if (!audio) {
            audio = new Audio(assetUrl({ ...playback.asset, ownerPackageId: playback.ownerPackageId })); audio.preload="auto"; instances.set(playback.id, audio);
            const seek=()=>seekToTimeline(audio,playback);
            if(typeof audio.addEventListener==="function") audio.addEventListener("loadedmetadata",seek,{once:true}); else seek();
        }
        audio.loop = Boolean(playback.loop);
        audio.__gravewrightPlayback = playback;
        // Logical gain composes with, and can never overwrite, the user's preference.
        fade(audio,playback);
        if((projections.get(playback.id)??1)<=0){audio.pause();pending.delete(playback.id);return;}
        if (!unlocked) { pending.add(playback.id); return; }
        if (playback.state === "paused") audio.pause(); else { try { await audio.play(); } catch { pending.add(playback.id); } }
    }
    async function unlock() {
        unlocked = true;
        for (const id of [...pending]) { pending.delete(id); const audio = instances.get(id); if (audio) { try { await audio.play(); } catch { pending.add(id); } } }
    }
    addEventListener("pointerdown", unlock, { once: true, capture: true });
    addEventListener("keydown", unlock, { once: true, capture: true });
    document.addEventListener("vtt:transport-event", async (event) => {
        const detail = event.detail || {};
        if (detail.event !== "audio.changed" || !detail.payload?.playback_id) return;
        await project(detail.payload.playback);
    });
    const inspect=id=>{const audio=instances.get(id),transition=transitions.get(id);return audio?Object.freeze({playing:!audio.paused,volume:audio.volume,effectiveGain:transition?.effectiveGain??null,fading:Boolean(transition)}):null;};
    function setPreference(channel,value){
        const channels=["master","music","ambience","sfx","cinematic"];
        if(!channels.includes(channel))throw new TypeError("invalid channel");
        const scalar=Math.max(0,Math.min(1,Number(value)));
        if(channel==="master"){
            localStorage.setItem("gravewright.audio.volume.master",String(scalar));
            for(const child of channels.slice(1)){
                if(storedPreference(child)>scalar)localStorage.setItem(`gravewright.audio.volume.${child}`,String(scalar));
            }
        }else{
            localStorage.setItem(`gravewright.audio.volume.${channel}`,String(Math.min(scalar,master())));
        }
        document.dispatchEvent(new CustomEvent("audio:preference-changed"));
    }
    function setMuted(value){localStorage.setItem("gravewright.audio.muted",value?"1":"0");document.dispatchEvent(new CustomEvent("audio:preference-changed"));}
    document.addEventListener("audio:preference-changed",()=>instances.forEach((audio,id)=>{const playback=audio.__gravewrightPlayback;if(playback)audio.volume=effective(playback.gain,playback.channel,id);}));
    function setAcousticProjection(id,value){const prior=projections.get(id)??0,scalar=Math.max(0,Math.min(1,Number(value)));projections.set(id,scalar);const audio=instances.get(id),playback=audio?.__gravewrightPlayback;if(!audio||!playback)return;audio.volume=effective(playback.gain,playback.channel,id);if(scalar<=0){audio.pause();pending.delete(id);return;}if(prior<=0)seekToTimeline(audio,playback);if(!unlocked){pending.add(id);return;}if(playback.state!=="paused"&&playback.state!=="stopped")audio.play().catch(()=>pending.add(id));}
    window.GravewrightAudioRuntime = Object.freeze({ project, unlock, preference, setPreference, setMuted, muted, inspect, setAcousticProjection });
    addEventListener("DOMContentLoaded",()=>{
        try { const context=JSON.parse(document.getElementById("gravewright-game-context")?.textContent||"{}"); for(const playback of context.audioPlaybacks||[]) void project(playback); } catch { /* malformed bootstrap fails closed */ }
    });
})();
