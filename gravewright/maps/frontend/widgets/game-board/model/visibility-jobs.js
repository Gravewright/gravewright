import { createVisibilityContext, visibilityPolygon } from './visibility-polygon.js';

/** Transfer only coordinates; the main thread never rebuilds point objects. */
export function visionPolygons(sources, radius, walls, context = createVisibilityContext(walls)) {
    return sources.map(source => {
        const points = visibilityPolygon(source, source.radius > 0 ? source.radius : radius, walls, context);
        const coordinates = new Float64Array(points.length * 2);
        for (let i = 0; i < points.length; i++) {
            coordinates[i * 2] = points[i].x;
            coordinates[i * 2 + 1] = points[i].y;
        }
        return coordinates;
    });
}

const workerFactory = () => typeof Worker === 'undefined' ? undefined :
    new Worker(new URL('./visibility-worker.js', import.meta.url), { type: 'module' });

/** One active calculation and one replaceable pending snapshot per mounted scene. */
export class VisibilityJobs {
    #walls;
    #context;
    #worker;
    #createWorker;
    #failed = false;
    #active;
    #pending;
    #sequence = 0;
    #closed = false;
    constructor(walls, createWorker = workerFactory) {
        this.#walls = walls;
        this.#createWorker = createWorker;
        this.#start();
    }
    #start() {
        if (this.#worker || this.#failed || this.#walls.length < 128) return;
        try {
            this.#worker = this.#createWorker();
            if (!this.#worker) return;
            this.#worker.onmessage = ({ data }) => this.#receive(data);
            this.#worker.onerror = event => { event.preventDefault?.(); this.#fallback(); };
            this.#worker.onmessageerror = () => this.#fallback();
            this.#worker.postMessage({ type: 'walls', walls: this.#walls });
        } catch { this.#fallback(); }
    }
    /**
     * Replace the wall snapshot and keep the worker. Callbacks of earlier requests
     * are revoked: the worker answers them in order, still with the old walls.
     */
    setWalls(walls) {
        if (this.#closed) return;
        this.cancel();
        this.#walls = walls;
        this.#context = undefined;
        if (!this.#worker) { this.#start(); return; }
        try { this.#worker.postMessage({ type: 'walls', walls }); }
        catch { this.#fallback(); }
    }
    request(sources, radius, apply) {
        if (this.#closed) return;
        const job = { id: ++this.#sequence, sources, radius, apply };
        if (!sources.length) { this.cancel(); apply([]); return; }
        if (!this.#worker) { this.#calculate(job); return; }
        if (this.#active) this.#pending = job;
        else this.#send(job);
    }
    #calculate(job) {
        this.#context ??= createVisibilityContext(this.#walls);
        job.apply?.(visionPolygons(job.sources, job.radius, this.#walls, this.#context));
    }
    #send(job) {
        this.#active = job;
        try { this.#worker.postMessage({ type: 'vision', id: job.id, sources: job.sources, radius: job.radius }); }
        catch { this.#fallback(); }
    }
    #receive(data) {
        if (this.#closed || data?.id !== this.#active?.id) return;
        if (!Array.isArray(data.polygons) || data.error) { this.#fallback(); return; }
        const active = this.#active;
        this.#active = undefined;
        active.apply?.(data.polygons);
        const next = this.#pending;
        this.#pending = undefined;
        if (next && !this.#closed) this.#send(next);
    }
    #fallback() {
        this.#worker?.terminate();
        this.#worker = undefined;
        // A worker that failed once (CSP, crash, clone error) is not restarted.
        this.#failed = true;
        const latest = this.#pending ?? this.#active;
        this.#pending = this.#active = undefined;
        if (latest && !this.#closed) this.#calculate(latest);
    }
    cancel() {
        this.#pending = undefined;
        if (this.#active) this.#active.apply = undefined;
    }
    dispose() {
        this.#closed = true;
        this.cancel();
        this.#worker?.terminate();
        this.#worker = this.#active = this.#context = undefined;
        this.#walls = [];
    }
}
