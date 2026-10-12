// gravewright/maps/frontend/shared/storage/browser-key-value-store.js
var BrowserKeyValueStore = class {
  open;
  constructor(open) {
    this.open = open;
  }
  read(key) {
    try {
      return this.open().getItem(key) ?? void 0;
    } catch {
      return void 0;
    }
  }
  write(key, value) {
    try {
      this.open().setItem(key, value);
    } catch {
    }
  }
  forget(key) {
    try {
      this.open().removeItem(key);
    } catch {
    }
  }
};
function browserStore(lifetime) {
  return new BrowserKeyValueStore(() => lifetime === "device" ? localStorage : sessionStorage);
}

// gravewright/maps/frontend/shared/rendering/presentation-profiles.js
var PRESENTATION_PROFILES = Object.freeze({
  scope: "player",
  default: "performance",
  profiles: Object.freeze({
    performance: Object.freeze({ backdropBlur: false, motion: "none", postProcessing: false, softShadows: false, particleDensity: 0.25, resolutionScale: 0.75 }),
    balanced: Object.freeze({ backdropBlur: true, motion: "reduced", postProcessing: false, softShadows: true, particleDensity: 0.5, resolutionScale: 1 }),
    quality: Object.freeze({ backdropBlur: true, motion: "full", postProcessing: true, softShadows: true, particleDensity: 1, resolutionScale: 1 })
  })
});

// gravewright/maps/frontend/shared/rendering/render-profile.js
var PROFILES = {
  performance: { name: "performance", capabilities: PRESENTATION_PROFILES.profiles.performance },
  balanced: { name: "balanced", capabilities: PRESENTATION_PROFILES.profiles.balanced },
  quality: { name: "quality", capabilities: PRESENTATION_PROFILES.profiles.quality }
};
function valid(value) {
  return value === "performance" || value === "balanced" || value === "quality";
}
var RenderProfilePreference = class {
  store;
  root;
  #listeners = /* @__PURE__ */ new Set();
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
  current() {
    return this.#profile;
  }
  subscribe(listener) {
    this.#listeners.add(listener);
    listener(this.#profile);
    return () => this.#listeners.delete(listener);
  }
  #key() {
    return `gravewright.render-profile.${this.#identity}`;
  }
  #apply() {
    if (this.root)
      this.root.dataset.renderProfile = this.#profile.name;
  }
  #announce() {
    for (const listener of [...this.#listeners])
      listener(this.#profile);
  }
};
var renderingPreferences = new RenderProfilePreference();
export {
  RenderProfilePreference,
  renderingPreferences
};
