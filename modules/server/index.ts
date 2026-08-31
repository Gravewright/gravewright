import express, { type NextFunction, type Request, type Response } from "express";
import type { Server } from "node:http";
import {
  defineModule,
  type BaseRequest,
  type BaseResponse,
  type MiddlewareHandler,
  type RouteHandler,
} from "@gravewright/sdk";

function requestOf(request: Request): BaseRequest {
  const headers = Object.fromEntries(Object.entries(request.headers).map(([name, value]) => [
    name,
    Array.isArray(value) ? value.join(", ") : value,
  ]));
  return {
    method: request.method,
    path: request.path,
    params: request.params as Record<string, string>,
    query: request.query as Record<string, string | string[] | undefined>,
    body: request.body,
    headers,
  };
}

function responseOf(response: Response): BaseResponse {
  const adapter: BaseResponse = {
    status(code) { response.status(code); return adapter; },
    json(value) { response.json(value); },
    text(value) {
      if (/^\s*<!doctype html>/i.test(value)) response.type("html");
      response.send(value);
    },
  };
  return adapter;
}

function configuredPort(): number {
  const raw = process.env.PORT ?? "3000";
  if (!/^\d+$/.test(raw)) throw new Error(`Invalid PORT: ${JSON.stringify(raw)}`);
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error(`Invalid PORT: ${JSON.stringify(raw)}`);
  return port;
}

export default defineModule({
  name: "server",
  kind: "server",
  provider: "core",
  version: "0.1.0",
  exports: { get: ["read", "write", "stat", "start", "stop", "route", "middleware", "slot", "port"] },
  create(_ctx) {
    const app = express();
    const mounts = new Set<string>();
    const slots = new Map<string, Set<unknown>>();
    let listener: Server | undefined;
    let port = configuredPort();
    app.disable("x-powered-by");
    app.use((_request, response, next) => {
      response.setHeader("x-content-type-options", "nosniff");
      response.setHeader("referrer-policy", "no-referrer");
      next();
    });
    app.use(express.json({ limit: "64kb", strict: true }));

    return {
      read(resource: string) {
        if (resource === "port") return port;
        throw new Error(`Unknown server resource: ${resource}`);
      },
      write(resource: string, value: unknown) {
        if (resource !== "port") throw new Error(`Unknown server resource: ${resource}`);
        if (listener) throw new Error("Cannot change the port while the server is running");
        if (!Number.isInteger(value) || (value as number) < 0 || (value as number) > 65535) throw new Error("Invalid server port");
        port = value as number;
      },
      stat() { return { running: listener !== undefined, port }; },
      get port() { return port; },
      route(mount: string, handler: RouteHandler) {
        if (mounts.has(mount)) throw new Error(`Route mount ${JSON.stringify(mount)} is already registered`);
        mounts.add(mount);
        let active = true;
        app.all(mount, async (request: Request, response: Response, next: NextFunction) => {
          if (!active) return next();
          try { await handler(requestOf(request), responseOf(response)); }
          catch (error) { next(error); }
        });
        return () => { active = false; mounts.delete(mount); };
      },
      middleware(mount: string, handler: MiddlewareHandler) {
        let active = true;
        app.use(mount, async (request: Request, response: Response, next: NextFunction) => {
          if (!active) return next();
          try { await handler(requestOf(request), responseOf(response), next); }
          catch (error) { next(error); }
        });
        return () => { active = false; };
      },
      slot(name: string, value: unknown) {
        const values = slots.get(name) ?? new Set();
        values.add(value); slots.set(name, values);
        return () => { values.delete(value); if (!values.size) slots.delete(name); };
      },
      async start() {
        if (listener) return;
        await new Promise<void>((resolve, reject) => {
          const candidate = app.listen(port, "127.0.0.1", () => {
            listener = candidate;
            const address = candidate.address();
            if (address && typeof address === "object") port = address.port;
            resolve();
          });
          candidate.once("error", reject);
        });
      },
      async stop() {
        const current = listener;
        listener = undefined;
        if (!current) return;
        await new Promise<void>((resolve, reject) => current.close((error) => error ? reject(error) : resolve()));
      },
    };
  },
});
