import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-chat",
  kind: "chat",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["send","erase"] },
  create(_ctx) {
    return {
      send(_message: string) { return crypto.randomUUID(); },
      erase(_messageId: string) {},
    };
  },
});
