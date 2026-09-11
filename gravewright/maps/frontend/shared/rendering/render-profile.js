import { browserStore } from "../storage/browser-key-value-store.js";
import { PRESENTATION_PROFILES } from "./presentation-profiles.js";
const PROFILES = {
    performance: { name: "performance", capabilities: PRESENTATION_PROFILES.profiles.performance },
    balanced: { name: "balanced", capabilities: PRESENTATION_PROFILES.profiles.balanced },
    quality: { name: "quality", capabilities: PRESENTATION_PROFILES.profiles.quality },
};
function valid(value) {
    return value === "performance" || value === "balanced" || value === "quality";
}
/** One local preference per authenticated person, independent of Table and Block. */
export class RenderProfilePreference {
    store;
    root;
    #listeners = new Set();
    #identity = "anonymous";
    #profile = PROFILES.performance;
    constructor(store = browserStore("device"), root = globalThis.document?.documentElement) {
        this.store = store;
        this.root = root;
        this.#apply();
    }
    activate(identity) {
        this.#identity = identity.trim().toLowerCase() || "anonymous";
        const saved = this.store.read(this.#key());
        this.#profile = PROFILES[valid(saved) ? saved : "performance"];
        this.#apply();
        this.#announce();
        return this.#profile;
    }
    select(name) {
        if (this.#profile.name === name)
            return;
        this.#profile = PROFILES[name];
        this.store.write(this.#key(), name);
        this.#apply();
        this.#announce();
    }
    current() { return this.#profile; }
    subscribe(listener) {
        this.#listeners.add(listener);
        listener(this.#profile);
        return () => this.#listeners.delete(listener);
    }
    #key() { return `gravewright.render-profile.${this.#identity}`; }
    #apply() { if (this.root)
        this.root.dataset.renderProfile = this.#profile.name; }
    #announce() { for (const listener of [...this.#listeners])
        listener(this.#profile); }
}
export const renderingPreferences = new RenderProfilePreference();
