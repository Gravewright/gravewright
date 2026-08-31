import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-backend",
  kind: "backend",
  provider: "community",
  version: "0.1.0",
  exports: { get: [] },
  create(_ctx) {
    return {
      // declare your exports here
    };
  },
});
