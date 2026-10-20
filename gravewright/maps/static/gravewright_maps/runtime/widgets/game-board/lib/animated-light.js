// gravewright/maps/frontend/widgets/game-board/lib/animated-light.js
import { Container, Sprite, Texture } from "/static/gravewright_maps/vendor/pixi.js";
import { lightAnimation, lightAnimationPhase, lightFalloff } from "../../../features/lighting/model/light-profiles.js";
var LightTexturePool = class {
  #textures = /* @__PURE__ */ new Map();
  get(color, flame) {
    const key = `${color}:${flame}`;
    let texture = this.#textures.get(key);
    if (!texture) {
      texture = Texture.from(lightFalloff(color, flame), true);
      this.#textures.set(key, texture);
    }
    return texture;
  }
  dispose() {
    for (const texture of this.#textures.values()) texture.destroy(true);
    this.#textures.clear();
  }
};
var AnimatedLight = class {
  node = new Container();
  animated;
  #light;
  #radius;
  #phase;
  #torch;
  #bright;
  #layers;
  constructor(light, radius, textures, now = 0) {
    this.#light = light;
    this.#radius = radius;
    this.#phase = lightAnimationPhase(light);
    this.#torch = ["torch", "candle", "fire"].includes(light.animation);
    this.animated = this.#torch || light.animation === "pulse";
    const bright = light.dim_radius > 0 ? light.bright_radius / light.dim_radius : 0.05;
    const layers = this.#torch ? [{ scale: 1, phase: 0, weight: 0.5 }, { scale: 0.62, phase: 2.1, weight: 0.4 }] : [{ scale: 1, phase: 0, weight: this.animated ? 0.55 : 0.5 }];
    this.#layers = layers.map((layer) => {
      const sprite = this.#sprite(textures.get(light.color, this.#torch));
      return { ...layer, sprite };
    });
    if (bright > 0) {
      this.#bright = this.#sprite(textures.get(light.color, false));
      this.#bright.width = this.#bright.height = radius * bright * 2;
    }
    this.node.position.set(light.x, light.y);
    this.update(now);
  }
  #sprite(texture) {
    const sprite = new Sprite(texture);
    sprite.anchor.set(0.5);
    sprite.blendMode = "add";
    this.node.addChild(sprite);
    return sprite;
  }
  update(now) {
    const light = this.#light, radius = this.#radius, phase = this.#phase;
    const torch = this.#torch;
    const bright = light.dim_radius > 0 ? light.bright_radius / light.dim_radius : 0.05;
    const reach = torch ? radius * (bright || 1) * 0.05 : 0;
    const x = torch ? Math.sin(now / 340 + phase) * reach : 0;
    const y = torch ? Math.sin(now / 470 + phase * 2) * reach : 0;
    const factor = light.intensity * lightAnimation(light, now, phase);
    for (let index = 0; index < this.#layers.length; index++) {
      const { sprite, scale, phase: offset, weight } = this.#layers[index];
      const p = phase + offset;
      let shape = 0.5;
      if (torch) {
        const v = p * 1.3 + 0.9;
        shape = 0.5 + 0.5 * (0.5 * Math.sin(now * 2 * Math.PI / (1300 * 0.7) + v) + 0.32 * Math.sin(now * 2 * Math.PI / (620 * 0.7) + v * 2) + 0.18 * Math.sin(now * 2 * Math.PI / (350 * 0.7) + v * 3));
      } else if (this.animated) {
        const wave = 0.5 + 0.5 * Math.sin(now * 2 * Math.PI / 2800 + p);
        shape = wave * wave * (3 - 2 * wave);
      }
      const r = radius * scale * (this.animated ? 1 + 0.3 * (shape - 0.5) * 2 : 1);
      sprite.position.set(
        x + (this.animated ? Math.sin(now / (380 + index * 47) + p) * radius * 0.025 : 0),
        y + (this.animated ? Math.sin(now / (530 + index * 61) + p * 1.7) * radius * 0.018 : 0)
      );
      sprite.rotation = torch ? (now / 1e3 * 0.05 * Math.PI * 2 + phase) * (index % 2 ? -1.6 : 1) : 0;
      sprite.width = sprite.height = r * 2;
      sprite.alpha = factor * weight;
    }
    if (this.#bright) {
      this.#bright.position.set(x, y);
      this.#bright.alpha = factor * 0.45;
    }
  }
};
export {
  AnimatedLight,
  LightTexturePool
};
