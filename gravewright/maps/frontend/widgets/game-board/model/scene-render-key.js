/** Snapshots are immutable. Reuse their serialized parts during local token drags. */
export class SceneRenderKey {
    #parts = new WeakMap();
    #imageSources = new WeakMap();
    part(value) {
        let key = this.#parts.get(value);
        if (key === undefined) {
            key = JSON.stringify(value);
            this.#parts.set(value, key);
        }
        return key;
    }
    imageSources(images) {
        let key = this.#imageSources.get(images);
        if (key === undefined) {
            key = JSON.stringify(images.map(({id, src}) => [id, src]));
            this.#imageSources.set(images, key);
        }
        return key;
    }
    static(state, cell, width, height, gm, profile) {
        return [state.containerId, state.blockId, state.sceneId, cell, width, height, gm, profile,
            this.imageSources(state.images),
            ...[state.walls, state.lights, state.particles, state.shaders, state.cards, state.zones, state.drawings, state.spatialSounds, state.lighting].map(value => value ? this.part(value) : '')].join('|');
    }
    vision(state) { return `${!!state.previewTokenVision}|${this.part(state.vision)}`; }
}
