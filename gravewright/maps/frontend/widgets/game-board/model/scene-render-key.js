/** Snapshots are immutable. Reuse their serialized parts during local token drags. */
export class SceneRenderKey {
    #parts = new WeakMap();
    part(value) {
        let key = this.#parts.get(value);
        if (key === undefined) {
            key = JSON.stringify(value);
            this.#parts.set(value, key);
        }
        return key;
    }
    static(state, cell, width, height, gm, profile) {
        return [state.containerId, state.blockId, state.sceneId, cell, width, height, gm, profile,
            ...[state.walls, state.lights, state.particles, state.shaders, state.images, state.cards, state.zones, state.drawings, state.spatialSounds, state.lighting].map(value => value ? this.part(value) : '')].join('|');
    }
    vision(state) { return `${!!state.previewTokenVision}|${this.part(state.vision)}`; }
}
