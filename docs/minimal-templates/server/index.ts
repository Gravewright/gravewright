import {
  defineModule,
  type MiddlewareHandler,
  type RouteHandler,
} from "@gravewright/sdk";

export default defineModule({
  name: "my-server",
  kind: "server",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["start", "stop", "route", "middleware", "slot"] },
  create(_ctx) {
    return {
      async start() {},
      async stop() {},
      route(_mount: string, _handler: RouteHandler) {
        return () => {};
      },
      middleware(_mount: string, _handler: MiddlewareHandler) {
        return () => {};
      },
      slot(_name: string, _value: unknown) {
        return () => {};
      },
    };
  },
});
