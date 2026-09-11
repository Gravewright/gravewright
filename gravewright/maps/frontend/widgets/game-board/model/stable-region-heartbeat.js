/** Announces changes after stabilization, then renews the settled viewport lease. */
export class StableRegionHeartbeat {
    same;
    emit;
    scheduler;
    settleMs;
    heartbeatMs;
    #settleTimer;
    #heartbeatTimer;
    #settled;
    constructor(same, emit, scheduler, settleMs = 300, heartbeatMs = 1000) {
        this.same = same;
        this.emit = emit;
        this.scheduler = scheduler;
        this.settleMs = settleMs;
        this.heartbeatMs = heartbeatMs;
    }
    changed(value) {
        this.#cancel(this.#settleTimer);
        this.#cancel(this.#heartbeatTimer);
        this.#heartbeatTimer = undefined;
        this.#settleTimer = this.scheduler.after(this.settleMs, () => {
            this.#settleTimer = undefined;
            if (!this.same(this.#settled, value))
                this.emit(value);
            this.#settled = value;
            this.#scheduleHeartbeat();
        });
    }
    stop() {
        this.#cancel(this.#settleTimer);
        this.#cancel(this.#heartbeatTimer);
        this.#settleTimer = undefined;
        this.#heartbeatTimer = undefined;
        this.#settled = undefined;
    }
    #scheduleHeartbeat() {
        this.#cancel(this.#heartbeatTimer);
        this.#heartbeatTimer = this.scheduler.after(this.heartbeatMs, () => {
            this.#heartbeatTimer = undefined;
            if (this.#settled !== undefined)
                this.emit(this.#settled);
            this.#scheduleHeartbeat();
        });
    }
    #cancel(id) { if (id !== undefined)
        this.scheduler.cancel(id); }
}
