const DOMAIN_NAMES = ["actor.directory", "actor.sheet", "token.sheet", "item.directory", "item.sheet", "scene.directory", "scene.controls", "scene.overlay", "chat.log", "combat.tracker", "journal.sheet", "preferences", "table.interface"];
const OPERATION_TRANSPORTS = { "actor.list": "json", "actor.read": "json", "actor.create": "json", "actor.update": "json", "actor.data.read": "json", "actor.data.update": "json", "actor.delete": "json", "token.read": "json", "token.move": "json", "token.data.read": "json", "token.data.update": "json", "asset.list": "json", "asset.upload": "multipart", "asset.download": "binary", "actor.image.upload": "multipart", "locale.apply": "json" };
export {
  DOMAIN_NAMES,
  OPERATION_TRANSPORTS
};
