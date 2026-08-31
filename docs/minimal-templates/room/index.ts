import { defineModule, ROOM_SLOT_NAMES } from "@gravewright/sdk";

export default defineModule({
  name: "my-room",
  kind: "room",
  provider: "community",
  version: "0.1.0",
  exposes: { slots: ROOM_SLOT_NAMES.map((name) => ({ name, mounts: "one", contributions: "many" })) },
  exports: { get: ["read", "write", "stat", "mount", "unmount"] },
  create(_ctx) {
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat(_resource?: string) { return {}; },
      mount(root: HTMLElement) {
        for (const name of ROOM_SLOT_NAMES) {
          const region = root.ownerDocument.createElement("div");
          region.className = name;
          root.append(region);
        }
      },
      unmount() {},
    };
  },
});
