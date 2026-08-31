import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-system",
  kind: "system",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["read", "write", "stat"] },
  create(_ctx) {
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat(_resource?: string) { return {}; },
    };
  },
});
