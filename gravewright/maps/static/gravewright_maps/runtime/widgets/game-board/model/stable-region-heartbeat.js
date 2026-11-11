// widgets/game-board/model/stable-region-heartbeat.js
var StableRegionHeartbeat = class {
  same;
  emit;
  scheduler;
  settleMs;
  heartbeatMs;
  #settleTimer;
  #heartbeatTimer;
  #settled;
  constructor(same, emit, scheduler, settleMs = 300, heartbeatMs = 1e3) {
    this.same = same;
    this.emit = emit;
    this.scheduler = scheduler;
    this.settleMs = settleMs;
    this.heartbeatMs = heartbeatMs;
  }
  changed(value) {
    this.#cancel(this.#settleTimer);
    this.#cancel(this.#heartbeatTimer);
    this.#heartbeatTimer = void 0;
    this.#settleTimer = this.scheduler.after(this.settleMs, () => {
      this.#settleTimer = void 0;
      if (!this.same(this.#settled, value))
        this.emit(value);
      this.#settled = value;
      this.#scheduleHeartbeat();
    });
  }
  stop() {
    this.#cancel(this.#settleTimer);
    this.#cancel(this.#heartbeatTimer);
    this.#settleTimer = void 0;
    this.#heartbeatTimer = void 0;
    this.#settled = void 0;
  }
  #scheduleHeartbeat() {
    this.#cancel(this.#heartbeatTimer);
    this.#heartbeatTimer = this.scheduler.after(this.heartbeatMs, () => {
      this.#heartbeatTimer = void 0;
      if (this.#settled !== void 0)
        this.emit(this.#settled);
      this.#scheduleHeartbeat();
    });
  }
  #cancel(id) {
    if (id !== void 0)
      this.scheduler.cancel(id);
  }
};
export {
  StableRegionHeartbeat
};
