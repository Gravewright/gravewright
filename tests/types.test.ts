import type { Context, ModuleAPI } from "@gravewright/sdk";

interface CharacterAPI extends ModuleAPI {
  get: {
    /** Aplica dano ao personagem. @param amount Quantidade de dano. */
    damage: (amount: number) => void;
  };
  set: { favoriteColor: string };
  prop: { hp: number };
}

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    character: CharacterAPI;
  }
}

declare const ctx: Context;

const character = ctx.use("character");
const hp: number = character.get("hp");
character.set("hp", 10);
void hp;
// @ts-expect-error hp is numeric
character.set("hp", "wrong");
// @ts-expect-error write-only values cannot be read
character.get("favoriteColor");
// @ts-expect-error read-only behavior cannot be overwritten
character.set("damage", () => {});

// @ts-expect-error unknown modules require the explicit DynamicContext fallback
ctx.use("unknown-module");

const server = ctx.use("server");
const start: () => Promise<void> = server.get("start");
const port: number = server.get("port");
void [start, port, server.get("middleware"), server.get("route"), server.get("slot")];
// @ts-expect-error port is read-only
server.set("port", 4000);
// @ts-expect-error unknown server export
server.get("unknown");

const marketplace = ctx.use("marketplace");
const install: (manifestUrl: string) => Promise<{ name: string; version: string }> = marketplace.get("install");
void [install, marketplace.get("list"), marketplace.get("marketplace")];
// @ts-expect-error unknown marketplace export
marketplace.get("notReal");
