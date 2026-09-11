import { HttpClient } from "../../../shared/api/http-client.js";
export class BlockStateApi {
    http;
    constructor(http = new HttpClient()) {
        this.http = http;
    }
    root(container, block) { return `/api/containers/${encodeURIComponent(container)}/blocks/${encodeURIComponent(block)}`; }
    state(container, block) { return this.http.get(`${this.root(container, block)}/state`, { cache: "no-store" }); }
    command(container, block, area, action, data = {}) { return this.http.post(`${this.root(container, block)}/commands/${encodeURIComponent(area)}/${encodeURIComponent(action)}`, data); }
}
