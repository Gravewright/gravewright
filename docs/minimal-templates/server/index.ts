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
  exports: { get: ["read", "write", "stat", "start", "stop", "route", "middleware", "slot"] },
  create(_ctx) {
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat(_resource?: string) { return {}; },
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
