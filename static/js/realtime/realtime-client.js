












(function () {
  const WEBSOCKET_RECONNECT_MS = 2000;

  let socket = null;
  let isSocketOpen = false;
  let reconnectTimer = null;
  let manualClose = false;
  const lastEventSeqByRoom = new Map();
  
  const pendingCommands = new Map();
  const STREAMER_ALLOWED_COMMANDS = new Set([
    "chunk.ack",
    "session.resume",
    "viewport.subscribe",
    "viewport.update",
  ]);

  function getWebSocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/game/ws`;
  }

  function scheduleReconnect() {
    if (reconnectTimer || manualClose || document.visibilityState === "hidden") {
      return;
    }

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connectWebSocket();
    }, WEBSOCKET_RECONNECT_MS);
  }

  function routeEnvelope(envelope) {
    const router = window.GravewrightRealtimeEvents;
    if (router && typeof router.process === "function") {
      router.process(envelope);
    }
  }

  function connectWebSocket() {
    if (!("WebSocket" in window)) {
      return;
    }

    if (
      socket &&
      (socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    manualClose = false;

    try {
      socket = new WebSocket(getWebSocketUrl());
      socket.binaryType = "arraybuffer";
    } catch {
      scheduleReconnect();
      return;
    }

    socket.addEventListener("open", () => {
      isSocketOpen = true;
      document.dispatchEvent(new CustomEvent("vtt:ws-open"));
    });

    socket.addEventListener("message", (event) => {
      if (event.data instanceof ArrayBuffer) {
        document.dispatchEvent(
          new CustomEvent("vtt:binary-frame", { detail: event.data })
        );
        return;
      }

      let envelope;
      try {
        envelope = JSON.parse(event.data);
      } catch {
        return;
      }

      if (envelope.event === "pong") {
        return;
      }

      if (envelope.type === "error") {
        const cmd = pendingCommands.get(envelope.command_id) || "?";
        pendingCommands.delete(envelope.command_id);
        console.error(
          `Realtime command failed: ${cmd} [${envelope.code || "unknown"}] ${envelope.message || ""}`,
          envelope
        );
        return;
      }

      if (envelope.command_id) {
        pendingCommands.delete(envelope.command_id);
      }

      routeEnvelope(envelope);
    });

    socket.addEventListener("close", () => {
      isSocketOpen = false;
      socket = null;
      document.dispatchEvent(new CustomEvent("vtt:ws-close"));
      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      if (socket) {
        socket.close();
      }
    });
  }

  function sendCommand(command, payload = {}, options = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    if (document.body?.dataset?.streamerMode === "true" && !STREAMER_ALLOWED_COMMANDS.has(command)) {
      return false;
    }

    const envelope = {
      type: "command",
      id: options.id || `cmd-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      command,
      payload,
    };

    if (options.roomId) {
      envelope.room_id = options.roomId;
    }

    if (options.sceneId) {
      envelope.scene_id = options.sceneId;
    }

    
    if (pendingCommands.size > 100) pendingCommands.clear();
    pendingCommands.set(envelope.id, command);

    socket.send(JSON.stringify(envelope));
    return true;
  }

  function disconnect() {
    manualClose = true;
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket) {
      socket.close();
    }
  }

  

  function recordEventSeq(eventEnvelope) {
    const roomId = eventEnvelope?.room_id || eventEnvelope?.payload?.room_id;
    const eventSeq = eventEnvelope?.event_seq;
    if (!roomId || !Number.isInteger(eventSeq)) return;

    const previousSeq = lastEventSeqByRoom.get(roomId) || 0;
    if (eventSeq > previousSeq) {
      lastEventSeqByRoom.set(roomId, eventSeq);
    }
  }

  function lastEventSeq(roomId) {
    return lastEventSeqByRoom.get(roomId) || 0;
  }

  document.addEventListener("vtt:transport-event", (event) => {
    recordEventSeq(event.detail);
  });

  
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      connectWebSocket();
    }
  });

  function status() {
    return {
      open: isSocketOpen,
      readyState: socket ? socket.readyState : null,
      pendingCommands: pendingCommands.size,
    };
  }

  function debugSnapshot() {
    return {
      ...status(),
      rooms: Object.fromEntries(lastEventSeqByRoom),
    };
  }

  connectWebSocket();

  window.GravewrightRealtime = {
    isOpen: () => isSocketOpen,
    sendCommand,
    send: sendCommand,
    lastEventSeq,
    connect: connectWebSocket,
    disconnect,
    status,
    debugSnapshot,
  };
})();
