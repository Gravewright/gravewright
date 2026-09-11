/** Stable SDK error code; callers should not branch on the display message. */
class ModuleError extends Error {
  constructor(code, message = code) {
    super(message);
    this.code = code;
    this.name = "GravewrightError";
  }
  code;
}
/**
 * Own cancellation and cleanup for a page, activation, or surface. Closing aborts
 * first and attempts every cleanup in reverse order, even if another one fails.
 */
class Lifetime {
  constructor(report = console.error) {
    this.report = report;
  }
  report;
  controller = new AbortController();
  signal = this.controller.signal;
  cleanups = [];
  closing;
  check() {
    if (this.signal.aborted) throw new ModuleError("stale_context");
  }
  onDispose = (cleanup) => {
    this.check();
    this.cleanups.push(cleanup);
  };
  /** Internal parent-child linkage can be released on every visual remount. */
  link(cleanup) {
    this.onDispose(cleanup);
    return () => {
      const index = this.cleanups.indexOf(cleanup);
      if (index >= 0) this.cleanups.splice(index, 1);
    };
  }
  close() {
    if (this.closing) return this.closing;
    this.controller.abort();
    const pending = [];
    for (const cleanup of this.cleanups.splice(0).reverse()) {
      try {
        const result = cleanup();
        if (result) pending.push(boundedCleanup(result).catch(this.report));
      } catch (error) {
        this.report(error);
      }
    }
    return this.closing = Promise.all(pending).then(() => {
    });
  }
  async wait(work, external) {
    // A caller abort is cancelled; owner disposal is stale_context. Neither rolls
    // back a mutation that has already committed on the server.
    this.check();
    const signal = external ? AbortSignal.any([this.signal, external]) : this.signal;
    if (signal.aborted) throw new ModuleError("cancelled");
    let cancel;
    const aborted = new Promise((_, reject) => {
      cancel = () => reject(new ModuleError(this.signal.aborted ? "stale_context" : "cancelled"));
      signal.addEventListener("abort", cancel, { once: true });
    });
    try {
      const value = await Promise.race([work(signal), aborted]);
      this.check();
      if (signal.aborted) throw new ModuleError("cancelled");
      return value;
    } finally {
      signal.removeEventListener("abort", cancel);
    }
  }
}
async function boundedCleanup(work) {
  let timer;
  try {
    await Promise.race([work, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new ModuleError("unavailable", "Module cleanup timed out")), 5e3);
    })]);
  } finally {
    clearTimeout(timer);
  }
}
export {
  Lifetime,
  ModuleError,
  boundedCleanup
};
