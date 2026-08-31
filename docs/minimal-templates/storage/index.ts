import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "my-storage",
  kind: "storage",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["create","find","where","update","delete"] },
  create(_ctx) {
    return {
      create(_collection: string, value: unknown) { return value; },
      find(_collection: string, _id: string) { return undefined; },
      where(_collection: string, _filters: Record<string, unknown>) { return []; },
      update(_collection: string, _id: string, value: unknown) { return value; },
      delete(_collection: string, _id: string) {},
    };
  },
});
