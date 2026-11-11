// widgets/game-board/model/scene-render-key.js
var SceneRenderKey = class {
  #parts = /* @__PURE__ */ new WeakMap();
  #imageSources = /* @__PURE__ */ new WeakMap();
  #staticInputs = [];
  #staticKey;
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
  static(state, cell, width, height, gm, profile) {
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
      state.spatialSounds,
      state.lighting
    ];
    if (inputs.every((value, index) => value === this.#staticInputs[index])) return this.#staticKey;
    this.#staticInputs = inputs;
    return this.#staticKey = [
      state.containerId,
      state.blockId,
      state.sceneId,
      cell,
      width,
      height,
      gm,
      profile,
      this.imageSources(state.images),
      ...[state.walls, state.lights, state.particles, state.shaders, state.cards, state.drawings, state.spatialSounds, state.lighting].map((value) => value ? this.part(value) : "")
    ].join("|");
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
