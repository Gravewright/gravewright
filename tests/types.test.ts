import type { Context, ModuleAPI } from "@gravewright/sdk";

interface CharacterAPI extends ModuleAPI {
  get: {
    /** Aplica dano ao personagem. @param amount Quantidade de dano. */
    damage: (amount: number) => void;
    hp: () => number;
    setFavoriteColor: (color: string) => void;
  };
}

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    character: CharacterAPI;
  }
}

declare const ctx: Context;

const character = ctx.use("character");
const hp: number = character.get("hp")();
character.get("setFavoriteColor")("purple");
void hp;
// @ts-expect-error hp does not accept arguments
character.get("hp")(10);
// @ts-expect-error color must be a string
character.get("setFavoriteColor")(42);

// @ts-expect-error unknown modules require the explicit DynamicContext fallback
ctx.use("unknown-module");

const server = ctx.use("gravewright-server");
const start: () => Promise<void> = server.get("start");
const port: number = server.get("port");
void [start, port, server.get("middleware"), server.get("route"), server.get("slot")];
// @ts-expect-error unknown server export
server.get("unknown");

const marketplace = ctx.use("gravewright-marketplace");
const install: (manifestUrl: string) => Promise<{ name: string; version: string }> = marketplace.get("install");
void [install, marketplace.get("list"), marketplace.get("marketplace")];
// @ts-expect-error unknown marketplace export
marketplace.get("notReal");
