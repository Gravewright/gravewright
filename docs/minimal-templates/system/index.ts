import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-system",
  kind: "system",
  provider: "community",
  version: "0.1.0",
  exports: { get: [] },
  create(_ctx) {
    return {
      // Declare your platform service commands here and add them to exports.get.
    };
  },
});
