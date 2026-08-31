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
  exports: { get: ["start", "stop", "http", "route", "middleware"] },
  create(_ctx) {
    return {
      http: {},
      async start() {},
      async stop() {},
      route(_mount: string, _handler: RouteHandler) {
        return () => {};
      },
      middleware(_mount: string, _handler: MiddlewareHandler) {
        return () => {};
      },
    };
  },
});
