import { defineModule, type AssetsKindAPI, type ChatKindAPI, type Context, type DiceEngineKindAPI, type DynamicContext, type ModuleAPI, type ModuleRef, type RoomKindAPI, type RulesetKindAPI, type ServerKindAPI, type StorageKindAPI } from "@gravewright/sdk";

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
declare const dynamicContext: DynamicContext;

const serverByKind: ServerKindAPI["get"]["http"] = ctx.kind("server").get("http");
const optionalRoom = ctx.kind("room");
let roomByKind: RoomKindAPI["get"]["slots"] | undefined;
if (optionalRoom) roomByKind = optionalRoom.get("slots");
const rulesetByKind: ModuleRef<RulesetKindAPI> | undefined = ctx.kind("ruleset");
const optionalChat = ctx.kind("chat");
if (optionalChat) {
  const send: ChatKindAPI["get"]["send"] = optionalChat.get("send");
  const erase: ChatKindAPI["get"]["erase"] = optionalChat.get("erase");
  void [send, erase];
}
const optionalDice = ctx.kind("dice-engine");
if (optionalDice) { const roll: DiceEngineKindAPI["get"]["roll"] = optionalDice.get("roll"); void roll; }
const optionalAssets = ctx.kind("assets");
if (optionalAssets) {
  const store: AssetsKindAPI["get"]["store"] = optionalAssets.get("store");
  const resolve: AssetsKindAPI["get"]["resolve"] = optionalAssets.get("resolve");
  void [store, resolve, optionalAssets.get("mimeTypeAllowed"), optionalAssets.get("remove")];
}
const optionalStorage = ctx.kind("storage");
if (optionalStorage) {
  const create: StorageKindAPI["get"]["create"] = optionalStorage.get("create");
  void [create, optionalStorage.get("find"), optionalStorage.get("where"), optionalStorage.get("update"), optionalStorage.get("delete")];
}
const pluralBackends = ctx.kind("backend");
void [serverByKind, roomByKind, rulesetByKind, optionalChat, optionalDice, optionalAssets, optionalStorage, pluralBackends];

defineModule({
  name: "invalid-chat-type-test", kind: "chat", provider: "community", version: "1.0.0", exports: { get: [] },
  // @ts-expect-error chat implementations must provide send and erase
  create() { return {}; },
});

defineModule({
  name: "invalid-server-type-test", kind: "server", provider: "community", version: "1.0.0", exports: { get: [] },
  // @ts-expect-error server implementations must provide the complete minimum contract
  create() { return { start() {}, stop() {} }; },
});

const dynamicFromTypedContext: DynamicContext = ctx;
dynamicContext.diagnostic.record({
  event: "types.dynamic-context",
  actor: "Test",
  action: "Verify diagnostic parity",
  status: "success",
});
void dynamicFromTypedContext;

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
void [start, port, server.get("middleware"), server.get("route"), server.get("realtime")];
// @ts-expect-error unknown server export
server.get("unknown");

const marketplace = ctx.use("gravewright-marketplace");
const install: (manifestUrl: string) => Promise<{ name: string; version: string }> = marketplace.get("install");
void [install, marketplace.get("list"), marketplace.get("marketplace")];
// @ts-expect-error unknown marketplace export
marketplace.get("notReal");
