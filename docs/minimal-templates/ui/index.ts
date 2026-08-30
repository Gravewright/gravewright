import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-ui",
  kind: "ui",
  provider: "community",
  version: "0.1.0",
  exports: { get: [] },
  create(_ctx) {
    return {
      // Declare public capabilities here and add their names to exports.get.
    };
  },
});
