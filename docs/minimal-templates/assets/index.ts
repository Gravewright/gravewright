import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-assets",
  kind: "assets",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["store","resolve","mimeTypeAllowed","remove"] },
  create(_ctx) {
    return {
      store(_asset: unknown) { return crypto.randomUUID(); },
      resolve(_id: string) { return undefined; },
      mimeTypeAllowed(_mimeType: string) { return true; },
      remove(_id: string) {},
    };
  },
});
