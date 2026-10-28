// widgets/game-board/lib/pixi-application.js
import { Application, BufferImageSource, Texture } from "/static/gravewright_maps/vendor/pixi.js";
Texture.WHITE.source.alphaMode = "premultiplied-alpha";
var emptySource = Texture.EMPTY.source;
Texture.EMPTY.source = new BufferImageSource({
  resource: new Uint8Array(4),
  width: 1,
  height: 1,
  alphaMode: "premultiplied-alpha",
  label: "EMPTY"
});
emptySource.destroy();
async function createPixiApplication(options) {
  const canvas = document.createElement("canvas");
  const attributes = {
    alpha: (options.backgroundAlpha ?? 1) < 1,
    premultipliedAlpha: true,
    antialias: options.antialias ?? false,
    stencil: true
  };
  const context = canvas.getContext("webgl2", attributes) || canvas.getContext("webgl", attributes);
  if (!context) throw new Error("WebGL is unavailable.");
  const application = new Application();
  try {
    await application.init({ ...options, canvas, context, preference: ["webgl"] });
    return application;
  } catch (error) {
    try {
      if (application.renderer) application.destroy(false, { children: true });
      else context.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
    }
    throw error;
  }
}
export {
  createPixiApplication
};
