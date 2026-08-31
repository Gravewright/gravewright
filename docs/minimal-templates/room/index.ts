import { defineModule, ROOM_PROTOCOL, ROOM_SLOT_NAMES } from "@gravewright/sdk";

export default defineModule({
  name: "my-room",
  kind: "room",
  provider: "community",
  version: "0.1.0",
  room_protocol: ROOM_PROTOCOL,
  exposes: { slots: ROOM_SLOT_NAMES.map((name) => ({ name, mounts: "one", contributions: "many" })) },
  exports: { get: ["mount", "unmount", "slots"] },
  create(_ctx) {
    return {
      mount(root: HTMLElement) {
        for (const name of ROOM_SLOT_NAMES) {
          const region = root.ownerDocument.createElement("div");
          region.className = name;
          root.append(region);
        }
      },
      unmount() {},
      slots(_name: string, _module: string, _value: unknown) { return () => {}; },
    };
  },
});
