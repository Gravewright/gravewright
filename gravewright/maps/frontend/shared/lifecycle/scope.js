/** A resource belongs to exactly one lifetime. Disposal is idempotent and aborts first. */
export class ResourceScope {
    #abort = new AbortController();
    #cleanups = [];
    get signal() { return this.#abort.signal; }
    get closed() { return this.signal.aborted; }
    own(cleanup) {
        if (this.closed) {
            cleanup();
            return () => { };
        }
        this.#cleanups.push(cleanup);
        return () => { const i = this.#cleanups.indexOf(cleanup); if (i >= 0)
            this.#cleanups.splice(i, 1); };
    }
    dispose() {
        if (this.closed)
            return;
        this.#abort.abort();
        const errors = [];
        for (const cleanup of this.#cleanups.splice(0).reverse()) {
            try {
                cleanup();
            }
            catch (error) {
                errors.push(error);
            }
        }
        if (errors.length)
            throw new AggregateError(errors, "scope_cleanup_failed");
    }
}
/** Each mounted table has its own instance. A new visit to A never reuses an old visit to A. */
export class ContainerScope extends ResourceScope {
    containerId;
    block = new ResourceScope();
    blockId = "";
    constructor(containerId) {
        super();
        this.containerId = containerId;
        this.own(() => this.block.dispose());
    }
    enter(blockId) {
        if (this.closed)
            throw new Error("container_closed");
        if (this.blockId !== blockId) {
            this.block.dispose();
            this.block = new ResourceScope();
            this.blockId = blockId;
        }
        return this.block;
    }
}
