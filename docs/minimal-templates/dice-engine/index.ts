import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-dice-engine",
  kind: "dice-engine",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["roll"] },
  create(_ctx) {
    return {
      roll(_expression: string) { return 0; },
    };
  },
});
