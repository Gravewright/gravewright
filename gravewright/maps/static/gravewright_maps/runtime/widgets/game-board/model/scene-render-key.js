// widgets/game-board/model/scene-render-key.js
var SceneRenderKey = class {
  #parts = /* @__PURE__ */ new WeakMap();
  #imageSources = /* @__PURE__ */ new WeakMap();
  #layerInputs = [];
  #layerKeys;
  part(value) {
    let key = this.#parts.get(value);
    if (key === void 0) {
      key = JSON.stringify(value);
      this.#parts.set(value, key);
    }
    return key;
  }
  imageSources(images) {
    let key = this.#imageSources.get(images);
    if (key === void 0) {
      key = JSON.stringify(images.map((row) => [
        row.id,
        row.surface || row.surfacePlane ? row.src : void 0,
        row.surface,
        row.empty === true && [row.natural_width, row.natural_height],
        row.surfacePlane && [
          row.surfacePlane,
          row.x,
          row.y,
          row.rotation,
          row.scale,
          row.layer,
          row.z_index,
          row.natural_width,
          row.natural_height
        ]
      ]));
      this.#imageSources.set(images, key);
    }
    return key;
  }
  /**
   * One key per independently synchronized part of the scene. `base` changes
   * remount everything; any other key refreshes only what reads that input.
   * Spatial sounds are absent: nothing here draws them.
   */
  layers(state, cell, width, height, gm, profile) {
    const inputs = [
      state.containerId,
      state.blockId,
      state.sceneId,
      cell,
      width,
      height,
      gm,
      profile,
      state.images,
      state.walls,
      state.lights,
      state.particles,
      state.shaders,
      state.cards,
      state.drawings,
      state.lighting
    ];
    if (this.#layerKeys && inputs.every((value, index) => value === this.#layerInputs[index])) return this.#layerKeys;
    this.#layerInputs = inputs;
    const part = (value) => value ? this.part(value) : "";
    return this.#layerKeys = {
      base: JSON.stringify([state.containerId, state.blockId, state.sceneId, cell, width, height, gm, profile]),
      images: this.imageSources(state.images),
      walls: part(state.walls),
      lights: part(state.lights),
      particles: part(state.particles),
      shaders: part(state.shaders),
      cards: part(state.cards),
      drawings: part(state.drawings),
      lighting: part(state.lighting)
    };
  }
  zones(state) {
    return state.zones ? this.part(state.zones) : "";
  }
  vision(state) {
    return `${!!state.previewTokenVision}|${this.part(state.vision)}`;
  }
};
export {
  SceneRenderKey
};
