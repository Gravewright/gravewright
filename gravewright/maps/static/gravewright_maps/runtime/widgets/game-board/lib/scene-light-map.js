// gravewright/maps/frontend/widgets/game-board/lib/scene-light-map.js
import { Container, Graphics, RenderTexture, Texture } from "/static/gravewright_maps/vendor/pixi.js";
import { paintAnimatedLight } from "../../../features/lighting/model/light-profiles.js";
import { AnimatedLight, LightTexturePool } from "./animated-light.js";
var SceneLightMap = class {
  ambient;
  canvas = document.createElement("canvas");
  texture;
  context;
  scale;
  #pixels;
  #renderToTexture;
  #scene;
  #textures;
  #ownsTextures;
  #stamps;
  #lights = [];
  #lastRead = -Infinity;
  #sampleOnly;
  constructor(width, height, edge, ambient, { renderToTexture, textures, sampleOnly = false } = {}) {
    this.ambient = ambient;
    this.scale = Math.min(1, edge / Math.max(width, height));
    this.canvas.width = Math.max(1, Math.ceil(width * this.scale));
    this.canvas.height = Math.max(1, Math.ceil(height * this.scale));
    this.#sampleOnly = sampleOnly;
    this.#renderToTexture = !sampleOnly && renderToTexture;
    if (sampleOnly) {
      this.texture = Texture.EMPTY;
    } else if (renderToTexture) {
      this.texture = RenderTexture.create({ width: this.canvas.width, height: this.canvas.height });
      this.#scene = new Container();
      this.#scene.scale.set(this.scale);
      this.#textures = textures ?? new LightTexturePool();
      this.#ownsTextures = !textures;
    } else {
      this.texture = Texture.from(this.canvas, true);
    }
  }
  #mount(stamps, now) {
    if (stamps === this.#stamps) return;
    for (const node of this.#scene.removeChildren()) node.destroy({ children: true });
    this.#lights = [];
    for (const stamp of stamps) {
      const group = new Container();
      const mask = new Graphics().poly(stamp.polygon.flatMap((p) => [p.x, p.y])).fill("white");
      const light = new AnimatedLight(stamp.light, stamp.radius, this.#textures, now);
      light.node.mask = mask;
      group.addChild(mask, light.node);
      this.#scene.addChild(group);
      if (light.animated) this.#lights.push(light);
    }
    this.#stamps = stamps;
  }
  #paint(stamps, now) {
    const ctx = this.context ??= this.canvas.getContext("2d", { willReadFrequently: true });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.scale(this.scale, this.scale);
    for (const stamp of stamps) {
      ctx.save();
      ctx.beginPath();
      stamp.polygon.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
      ctx.closePath();
      ctx.clip();
      if (stamp.light) paintAnimatedLight(ctx, stamp.light, stamp.x, stamp.y, stamp.radius, now);
      else {
        ctx.globalCompositeOperation = "lighter";
        ctx.drawImage(stamp.canvas, stamp.x - stamp.radius, stamp.y - stamp.radius, stamp.radius * 2, stamp.radius * 2);
      }
      ctx.restore();
    }
  }
  update(stamps, readPixels, now = performance.now()) {
    if (this.#renderToTexture) {
      this.#mount(stamps, now);
      for (const light of this.#lights) light.update(now);
      this.#renderToTexture(this.#scene, this.texture);
    } else if (!this.#sampleOnly) {
      this.#paint(stamps, now);
      this.texture.source.update();
    }
    if (readPixels && (now - this.#lastRead >= 125 || !this.#pixels)) {
      if (this.#renderToTexture || this.#sampleOnly) this.#paint(stamps, now);
      this.#pixels = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height).data;
      this.#lastRead = now;
    } else if (!readPixels) this.#pixels = void 0;
  }
  tint(color, x, y, response) {
    const base = parseInt(color.slice(1), 16), pixels = this.#pixels;
    if (!pixels || response <= 0)
      return base;
    const px = Math.max(0, Math.min(this.canvas.width - 1, Math.floor(x * this.scale))), py = Math.max(0, Math.min(this.canvas.height - 1, Math.floor(y * this.scale))), index = (py * this.canvas.width + px) * 4;
    let output = 0;
    for (let c = 0; c < 3; c++) {
      const shift = 16 - c * 8, channel = (base >> shift & 255) / 255;
      const illumination = Math.min(1.5, this.ambient + (pixels[index + c] ?? 0) / 255 * (pixels[index + 3] ?? 0) / 255);
      const value = Math.pow(Math.pow(channel, 2.2) * (1 - response + response * illumination), 1 / 2.2);
      output |= Math.min(255, Math.round(value * 255)) << shift;
    }
    return output;
  }
  dispose() {
    this.#pixels = void 0;
    this.#lights = [];
    this.#stamps = void 0;
    this.#scene?.destroy({ children: true });
    if (this.#ownsTextures) this.#textures.dispose();
    if (this.texture !== Texture.EMPTY) this.texture.destroy(true);
    this.canvas.width = this.canvas.height = 1;
  }
};
export {
  SceneLightMap
};
