/* First-class core audio projection. Browser primitives never cross the SDK boundary. */
(() => {
    const instances = new Map();
    const pending = new Set();
    const transitions = new Map();
    const projections = new Map();
    let unlocked = false;
    let resumeInterval = 0;
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
    const shouldBePlaying=(playback,id)=>Boolean(playback&&playback.state!=="paused"&&playback.state!=="stopped"&&(projections.get(id)??1)>0);
    const pauseIntentionally=(audio)=>{audio.__gravewrightIntentionalPauseUntil=performance.now()+750;audio.pause();};
    async function resume(id){const audio=instances.get(id),playback=audio?.__gravewrightPlayback;if(!audio||!shouldBePlaying(playback,id))return;try{await audio.play();pending.delete(id);}catch{pending.add(id);}}
    const scheduleResume=(id,delay=180)=>window.setTimeout(()=>void resume(id),delay);
    const seekToTimeline=(audio,playback)=>{
        // A playback still pending the browser's autoplay unlock has never actually
        // sounded for anyone yet, so the wall-clock elapsed since startedAt is not a
        // real position - seeking to it could land past the track's end. Once the
        // server confirms first playback it resets startedAt, and this becomes a
        // true shared timeline for clients joining an already-playing track.
        if(playback.state==="pending-user-unlock")return;
        const elapsed=Math.max(0,Date.now()/1000-Number(playback.startedAt||Date.now()/1000));if(Number.isFinite(audio.duration)&&audio.duration>0)audio.currentTime=playback.loop?elapsed%audio.duration:Math.min(elapsed,Math.max(0,audio.duration-.05));
    };
    const cancelTransition=(id)=>{const prior=transitions.get(id);if(prior)cancelAnimationFrame(prior.frame);transitions.delete(id);};
    function fade(audio,playback){
        cancelTransition(playback.id);
        const spec=playback.fade;if(!spec||!Number(spec.durationMs)){audio.volume=effective(playback.gain,playback.channel,playback.id);return;}
        const now=Date.now(),started=Number(spec.startedAt||playback.updatedAt||playback.startedAt*1000||now);
        const duration=Math.max(0,Number(spec.durationMs));const from=Number.isFinite(Number(spec.fromGain))?Number(spec.fromGain):(spec.direction==="out"?Number(playback.gain):0);
        const to=spec.direction==="out"?0:Number(playback.gain);const state={from,to,started,duration,effectiveGain:from,frame:0};
        const tick=()=>{const ratio=Math.max(0,Math.min(1,(Date.now()-started)/duration));const eased=spec.curve==="ease-in"?ratio*ratio:spec.curve==="ease-out"?1-(1-ratio)*(1-ratio):ratio;state.effectiveGain=from+(to-from)*eased;audio.volume=effective(state.effectiveGain,playback.channel,playback.id);if(ratio<1){state.frame=requestAnimationFrame(tick);}else{transitions.delete(playback.id);if(spec.direction==="out"){pauseIntentionally(audio);instances.delete(playback.id);pending.delete(playback.id);}}};
        transitions.set(playback.id,state);tick();
    }
    async function project(playback) {
        if (!playback?.id) return;
        if(isNativeSpatial(playback)&&!projections.has(playback.id))projections.set(playback.id,0);
        let audio = instances.get(playback.id);
        if (playback.state === "stopped") { cancelTransition(playback.id); if (audio) { pauseIntentionally(audio); instances.delete(playback.id); } pending.delete(playback.id); return; }
        if (!audio) {
            audio = new Audio(assetUrl({ ...playback.asset, ownerPackageId: playback.ownerPackageId })); audio.preload="auto"; instances.set(playback.id, audio);
            const seek=()=>seekToTimeline(audio,playback);
            if(typeof audio.addEventListener==="function") audio.addEventListener("loadedmetadata",seek,{once:true}); else seek();
            if(typeof audio.addEventListener==="function"){
                audio.addEventListener("pause",()=>{if(performance.now()>Number(audio.__gravewrightIntentionalPauseUntil||0)&&shouldBePlaying(audio.__gravewrightPlayback,playback.id)){pending.add(playback.id);scheduleResume(playback.id);}});
                audio.addEventListener("ended",()=>{if(shouldBePlaying(audio.__gravewrightPlayback,playback.id)){pending.add(playback.id);seekToTimeline(audio,audio.__gravewrightPlayback);scheduleResume(playback.id);}});
                audio.addEventListener("error",()=>{if(shouldBePlaying(audio.__gravewrightPlayback,playback.id)){pending.add(playback.id);scheduleResume(playback.id,750);}});
            }
        }
        audio.loop = Boolean(playback.loop);
        audio.__gravewrightPlayback = playback;
        // Logical gain composes with, and can never overwrite, the user's preference.
        fade(audio,playback);
        if((projections.get(playback.id)??1)<=0){pauseIntentionally(audio);pending.delete(playback.id);return;}
        if (!unlocked) { pending.add(playback.id); return; }
        if (playback.state === "paused") { pauseIntentionally(audio); pending.delete(playback.id); } else await resume(playback.id);
    }
    async function unlock() {
        unlocked = true;
        for (const id of [...pending]) { pending.delete(id); await resume(id); }
    }
    // Autoplay pode continuar bloqueado mesmo depois da primeira interação
    // (troca de aba, webview e alguns navegadores móveis fazem isso). Mantemos
    // a ponte ativa para que qualquer nova interação tente novamente os sons
    // recebidos da mesa que ficaram pendentes.
    addEventListener("pointerdown", unlock, { capture: true });
    addEventListener("keydown", unlock, { capture: true });
    addEventListener("online",()=>instances.forEach((_audio,id)=>void resume(id)));
    addEventListener("pageshow",()=>instances.forEach((_audio,id)=>void resume(id)));
    document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")instances.forEach((_audio,id)=>void resume(id));});
    resumeInterval=window.setInterval(()=>{if(!unlocked)return;instances.forEach((audio,id)=>{if(audio.paused&&shouldBePlaying(audio.__gravewrightPlayback,id))void resume(id);});},3000);
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
    function setAcousticProjection(id,value){const prior=projections.get(id)??0,scalar=Math.max(0,Math.min(1,Number(value)));projections.set(id,scalar);const audio=instances.get(id),playback=audio?.__gravewrightPlayback;if(!audio||!playback)return;audio.volume=effective(playback.gain,playback.channel,id);if(scalar<=0){pauseIntentionally(audio);pending.delete(id);return;}if(prior<=0)seekToTimeline(audio,playback);if(!unlocked){pending.add(id);return;}void resume(id);}
    function teardown(){
        if(resumeInterval){clearInterval(resumeInterval);resumeInterval=0;}
        transitions.forEach((_transition,id)=>cancelTransition(id));
        instances.forEach((audio)=>{pauseIntentionally(audio);audio.removeAttribute?.("src");audio.load?.();});
        instances.clear();pending.clear();projections.clear();unlocked=false;
    }
    function projectBootstrap(){
        try { const context=JSON.parse(document.getElementById("gravewright-game-context")?.textContent||"{}"); for(const playback of context.audioPlaybacks||[]) void project(playback); } catch { /* malformed bootstrap fails closed */ }
    }
    async function resyncFromSnapshot(){
        // The realtime event log only replays a short TTL window, so a socket that
        // was offline longer than that (or just missed a broadcast) needs the
        // authoritative playback list, not just whatever replays land after reconnect.
        let campaignId="";
        try { campaignId=JSON.parse(document.getElementById("gravewright-game-context")?.textContent||"{}").campaign?.id||""; } catch { return; }
        if(!campaignId)return;
        let playbacks;
        try {
            const response=await fetch(`/game/audio/${encodeURIComponent(campaignId)}/playbacks`,{credentials:"same-origin"});
            if(!response.ok)return;
            playbacks=await response.json();
        } catch { return; }
        if(!Array.isArray(playbacks))return;
        const seen=new Set();
        for(const playback of playbacks){ if(!playback?.id)continue; seen.add(playback.id); void project(playback); }
        for(const id of [...instances.keys()]) if(!seen.has(id)) void project({id,state:"stopped"});
    }
    window.GravewrightAudioRuntime = Object.freeze({ project, unlock, preference, setPreference, setMuted, muted, inspect, setAcousticProjection, teardown });
    addEventListener("DOMContentLoaded",projectBootstrap);
    addEventListener("vtt:ws-open",()=>void resyncFromSnapshot());
    addEventListener("pagehide",teardown);
    addEventListener("vtt:game-exit",teardown);
    addEventListener("pageshow",event=>{if(event.persisted){if(!resumeInterval)resumeInterval=window.setInterval(()=>{if(!unlocked)return;instances.forEach((_audio,id)=>void resume(id));},3000);projectBootstrap();}});
})();
