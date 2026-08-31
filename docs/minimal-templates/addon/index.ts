import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-addon",
  kind: "addon",
  provider: "community",
  version: "0.1.0",
  exports: { get: [] },
  create(_ctx) {
    return {};
  },
});
