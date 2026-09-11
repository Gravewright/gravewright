/** Serializes a drain and starts a fresh pass when work arrives while that drain is awaiting. */
export class AsyncWorkPump {
    hasWork;
    drain;
    #running = false;
    constructor(hasWork, drain) {
        this.hasWork = hasWork;
        this.drain = drain;
    }
    request() {
        if (this.#running || !this.hasWork())
            return;
        void this.#run();
    }
    async #run() {
        this.#running = true;
        try {
            await this.drain();
        }
        finally {
            this.#running = false;
            if (this.hasWork())
                this.request();
        }
    }
}
