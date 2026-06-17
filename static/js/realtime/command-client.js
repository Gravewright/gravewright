








(function () {
  function realtime() {
    return window.GravewrightRealtime || null;
  }

  
  function send(command, payload = {}, options = {}) {
    const rt = realtime();
    return rt ? rt.sendCommand(command, payload, options) : false;
  }

  const Commands = {
    send,

    
    moveToken(payload, options) {
      return send("token.move", payload, options);
    },
    createToken(payload, options) {
      if (!payload || !payload.actor_id) return false;
      return send("token.create_many_from_actors", {
        scene_id: payload.scene_id,
        actor_ids: [payload.actor_id],
        origin: { grid_x: payload.grid_x, grid_y: payload.grid_y },
      }, options);
    },
    createTokensFromActors(payload, options) {
      return send("token.create_many_from_actors", payload, options);
    },
    removeTokenFromScene(payload, options) {
      return send("token.remove_from_scene", payload, options);
    },

    
    subscribeViewport(payload, options) {
      return send("viewport.subscribe", payload, options);
    },
    updateViewport(payload, options) {
      return send("viewport.update", payload, options);
    },
    ackChunk(payload, options) {
      return send("chunk.ack", payload, options);
    },

    
    resumeSession(payload, options) {
      return send("session.resume", payload, options);
    },
    boardPing(payload, options) {
      return send("board.ping", payload, options);
    },
  };

  window.GravewrightCommands = Commands;
})();
