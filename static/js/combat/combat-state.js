




(function () {
  const ROLE_META = {
    current: {
      role: "current",
      label: "Turno atual",
      color: 0x28d17c,
      alpha: 0.96,
    },
    next: {
      role: "next",
      label: "Próximo",
      color: 0xef4444,
      alpha: 0.92,
    },
    acted: {
      role: "acted",
      label: "Já atuou",
      color: 0x9ca3af,
      alpha: 0.68,
    },
  };

  const states = new Map();
  const markersByRoom = new Map();
  let animationFrame = 0;
  let lastAnimationAt = 0;

  function participantTokenId(participant) {
    return participant?.token_id || participant?.tokenId || "";
  }

  function participantId(participant) {
    return participant?.id || participant?.participant_id || "";
  }

  function currentIndexFor(state, participants) {
    if (!participants.length) return -1;
    const explicit = Number(state?.turn_index);
    if (Number.isInteger(explicit) && explicit >= 0 && explicit < participants.length) return explicit;

    const activeId = state?.current_participant_id || state?.active_participant_id || state?.current?.id || "";
    if (activeId) {
      const byId = participants.findIndex((participant) => participantId(participant) === activeId);
      if (byId >= 0) return byId;
    }

    const byFlag = participants.findIndex((participant) => participant?.is_current || participant?.is_active_turn);
    return byFlag >= 0 ? byFlag : 0;
  }

  function nextIndexFor(currentIndex, participants) {
    if (!participants.length || currentIndex < 0) return -1;
    if (participants.length === 1) return -1;
    return (currentIndex + 1) % participants.length;
  }

  function setMarker(markers, tokenId, role, participant) {
    if (!tokenId || !ROLE_META[role]) return;
    const meta = ROLE_META[role];
    markers.set(tokenId, {
      ...meta,
      participant_id: participantId(participant),
      initiative_label: participant?.initiative_label || "",
      name: participant?.name || "",
    });
  }

  function buildMarkers(state) {
    const markers = new Map();
    if (!state?.is_active) return markers;

    const participants = Array.isArray(state.participants) ? state.participants : [];
    if (!participants.length) return markers;

    
    
    
    participants.forEach((participant) => {
      if (participant?.has_acted || participant?.turn_status === "acted") {
        setMarker(markers, participantTokenId(participant), "acted", participant);
      }
    });

    const currentIndex = currentIndexFor(state, participants);
    const nextIndex = nextIndexFor(currentIndex, participants);
    if (nextIndex >= 0) {
      setMarker(markers, participantTokenId(participants[nextIndex]), "next", participants[nextIndex]);
    }
    if (currentIndex >= 0) {
      setMarker(markers, participantTokenId(participants[currentIndex]), "current", participants[currentIndex]);
    }

    return markers;
  }

  function hasAnimatedMarkers() {
    for (const markers of markersByRoom.values()) {
      for (const marker of markers.values()) {
        if (marker.role === "current" || marker.role === "next") return true;
      }
    }
    return false;
  }

  function stopAnimationLoop() {
    if (animationFrame) window.cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    lastAnimationAt = 0;
  }

  function animationLoop(now) {
    if (!hasAnimatedMarkers()) {
      stopAnimationLoop();
      return;
    }

    
    
    if (!lastAnimationAt || now - lastAnimationAt >= 55) {
      lastAnimationAt = now;
      window.GravewrightMap?.redraw?.();
    }
    animationFrame = window.requestAnimationFrame(animationLoop);
  }

  function ensureAnimationLoop() {
    if (animationFrame || !hasAnimatedMarkers()) return;
    animationFrame = window.requestAnimationFrame(animationLoop);
  }

  function set(roomId, state) {
    if (!roomId) return;
    states.set(roomId, state || {});
    markersByRoom.set(roomId, buildMarkers(state || {}));

    document.dispatchEvent(new CustomEvent("vtt:combat-state-changed", {
      detail: { roomId, state: state || {} },
    }));
    window.GravewrightMap?.redraw?.();
    ensureAnimationLoop();
  }

  function clear(roomId) {
    if (!roomId) return;
    states.delete(roomId);
    markersByRoom.delete(roomId);
    document.dispatchEvent(new CustomEvent("vtt:combat-state-changed", {
      detail: { roomId, state: null },
    }));
    window.GravewrightMap?.redraw?.();
    if (!hasAnimatedMarkers()) stopAnimationLoop();
  }

  function get(roomId) {
    return states.get(roomId) || null;
  }

  function markerForToken(roomId, tokenId) {
    if (!roomId || !tokenId) return null;
    return markersByRoom.get(roomId)?.get(tokenId) || null;
  }

  function roleForToken(roomId, tokenId) {
    return markerForToken(roomId, tokenId)?.role || "";
  }

  window.GravewrightCombatState = {
    clear,
    get,
    markerForToken,
    roleForToken,
    set,
  };
})();
