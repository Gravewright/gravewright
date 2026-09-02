import { defineModule, type ClientFrontend, type Context, type DynamicContext, type ModuleAPI } from "@gravewright/sdk";

interface CharacterAPI extends ModuleAPI { get: { hp: () => number; damage: (amount: number) => void } }
declare module "@gravewright/sdk" { interface ModuleRegistry { character: CharacterAPI } }
declare const ctx: Context;
declare const dynamic: DynamicContext;
declare const clientFrontend: ClientFrontend;
const character = ctx.use("character");
const hp: number = character.get("hp")(); character.get("damage")(1); void [hp, dynamic.use("dynamic")];
declare const browserRoot: HTMLElement;
void clientFrontend.mount(browserRoot);
clientFrontend.slot("sidebar", "character", { id: "character", mount() {} });
// @ts-expect-error concrete dependencies are typed by ModuleRegistry
ctx.use("unknown-module");
// @ts-expect-error only declared exports are visible
character.get("internal");
// @ts-expect-error kind-based resolution was removed
ctx.kind("module");
// @ts-expect-error capability-based resolution was removed
ctx.capability("storage");
defineModule({ name: "server", kind: "server", provider: "community", version: "1.0.0", exports: { get: ["start", "stop", "http", "route", "middleware"] }, create() { return { start() {}, stop() {}, http: {}, route: () => () => {}, middleware: () => () => {} }; } });
defineModule({ name: "frontend", kind: "frontend", provider: "community", version: "1.0.0", exports: { get: ["start", "stop"] }, create() { return { start() {}, stop() {} }; } });
defineModule({ name: "backend", kind: "backend", provider: "community", version: "1.0.0", exports: { get: ["start", "stop"] }, create() { return { start() {}, stop() {} }; } });
defineModule({ name: "free", kind: "module", provider: "community", version: "1.0.0", exports: { get: [] }, create() { return {}; } });
