// widgets/game-board/model/async-work-pump.js
var AsyncWorkPump = class {
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
    } finally {
      this.#running = false;
      if (this.hasWork())
        this.request();
    }
  }
};
export {
  AsyncWorkPump
};
