// Generated from contracts/frontend.json; run scripts/generate_frontend_api.py.
export const FRONTEND_CONTRACT = {
  "version": "1.2.0",
  "domains": {
    "mindmaps": {
      "create": "create",
      "update": "update",
      "node": "node",
      "delete": "delete",
      "read": "read",
      "resources": "resources",
      "resolve": "resolve"
    },
    "clues": {
      "create": "create",
      "update": "update",
      "advance": "advance",
      "reset": "reset",
      "reveal": "reveal",
      "hide": "hide",
      "delete": "delete"
    },
    "clocks": {
      "create": "create",
      "update": "update",
      "advance": "advance",
      "reset": "reset",
      "delete": "delete"
    },
    "actors": {
      "create": "actor.create",
      "update": "actor.update",
      "delete": "actor.delete",
      "setPermissions": "actor.permissions",
      "saveSheet": "sheet.save",
      "createFolder": "folder.create",
      "updateFolder": "folder.update",
      "deleteFolder": "folder.delete",
      "deleteAsset": "asset.delete"
    },
    "tokens": {
      "place": "place",
      "move": "move",
      "remove": "remove",
      "duplicate": "duplicate",
      "setHidden": "hidden",
      "setVision": "vision",
      "configure": "configure",
      "addCondition": "condition-add",
      "removeCondition": "condition-remove"
    },
    "maps": {
      "update": "update",
      "move": "move",
      "delete": "delete",
      "activate": "activate",
      "updateObjects": "objects",
      "createFolder": "folder-create",
      "updateFolder": "folder-update",
      "deleteFolder": "folder-delete",
      "navigate": "navigate",
      "exportUniversalVtt": "export-universal-vtt"
    },
    "journals": {
      "resources": "resources",
      "resolve": "resolve",
      "create": "create",
      "update": "update",
      "delete": "delete",
      "move": "move",
      "setAccess": "access",
      "present": "present",
      "createFolder": "folder-create",
      "updateFolder": "folder-update",
      "moveFolder": "folder-move",
      "deleteFolder": "folder-delete",
      "setStatus": "status",
      "setObjective": "objective",
      "assignCharacters": "assign",
      "createBoardQuest": "board-create",
      "addQuest": "board-add",
      "removeQuest": "board-remove",
      "pinQuest": "board-pin",
      "reorderQuests": "board-reorder",
      "roll": "roll",
      "reset": "reset",
      "setPrerequisites": "prerequisites",
      "restoreRevision": "restore-revision",
      "restoreDeleted": "restore-deleted",
      "purgeDeleted": "trash-purge"
    },
    "items": {
      "create": "create",
      "update": "update",
      "delete": "delete",
      "duplicate": "duplicate",
      "setPermissions": "permissions",
      "createFolder": "folder-create",
      "updateFolder": "folder-update",
      "deleteFolder": "folder-delete"
    },
    "combat": {
      "add": "add",
      "remove": "remove",
      "configure": "configure",
      "setInitiative": "initiative",
      "rollInitiative": "roll",
      "toggle": "toggle",
      "moveUp": "order-up",
      "moveDown": "order-down",
      "setTurn": "set-turn",
      "nextRound": "next-round",
      "previousRound": "previous-round",
      "start": "start",
      "stop": "stop",
      "nextTurn": "next",
      "previousTurn": "previous"
    },
    "cards": {
      "define": "define",
      "instantiate": "instantiate",
      "create": "create",
      "draw": "draw",
      "shuffle": "shuffle",
      "reset": "reset",
      "deleteDeck": "delete-deck",
      "discard": "discard",
      "return": "return",
      "give": "give",
      "place": "place",
      "take": "take",
      "flip": "flip",
      "move": "move"
    },
    "audio": {
      "updateTrack": "track-update",
      "deleteTrack": "track-delete",
      "createPlaylist": "playlist-create",
      "updatePlaylist": "playlist-update",
      "deletePlaylist": "playlist-delete",
      "createSpatialSound": "spatial-create",
      "updateSpatialSound": "spatial-update",
      "deleteSpatialSound": "spatial-delete",
      "play": "play",
      "pause": "pause",
      "stop": "stop",
      "seek": "seek",
      "setVolume": "volume",
      "startScore": "score-start",
      "pauseScore": "score-pause",
      "resumeScore": "score-resume",
      "stopScore": "score-stop",
      "nextScore": "score-next",
      "previousScore": "score-previous"
    },
    "compendiums": {
      "create": "create",
      "configure": "configure",
      "read": "read",
      "delete": "delete",
      "add": "add",
      "remove": "remove",
      "import": "import",
      "setPermissions": "permissions"
    },
    "mapBuilder": {
      "read": "read",
      "save": "save",
      "generate": "generate",
      "update": "update",
      "sync": "sync",
      "adopt": "adopt"
    },
    "blueprints": {
      "save": "save",
      "templates": "templates",
      "readTemplate": "readTemplate",
      "saveTemplate": "saveTemplate",
      "deleteTemplate": "deleteTemplate",
      "test": "test",
      "testDraft": "testDraft",
      "control": "control"
    },
    "library": {
      "createFolder": "folder-create",
      "updateFolder": "folder-rename",
      "deleteFolder": "folder-delete",
      "move": "move",
      "delete": "delete"
    },
    "system": {
      "call": "call"
    },
    "ownership": {
      "read": "read",
      "update": "update"
    }
  },
  "reads": {
    "mindmaps": [
      "read",
      "resources",
      "resolve"
    ],
    "journals": [
      "resources",
      "resolve"
    ],
    "actors": [
      "sheet"
    ],
    "maps": [
      "layers"
    ],
    "ownership": [
      "read"
    ]
  },
  "services": {
    "chat": [
      "history",
      "send",
      "remove",
      "clear"
    ],
    "dice": [
      "roll"
    ],
    "table": [
      "search",
      "lobby",
      "updateLobby"
    ]
  },
  "binary": {
    "maps": {
      "upload": "upload",
      "importUniversalVtt": "upload"
    },
    "library": {
      "upload": "upload",
      "download": "download"
    },
    "actors": {
      "uploadAsset": "upload",
      "uploadImage": "upload",
      "downloadAsset": "download"
    },
    "audio": {
      "upload": "upload"
    },
    "cards": {
      "uploadAsset": "upload"
    },
    "journals": {
      "uploadAsset": "upload",
      "downloadAsset": "download"
    }
  },
  "longRunning": {
    "mapBuilder": [
      "generate",
      "update"
    ],
    "maps": [
      "exportUniversalVtt"
    ],
    "blueprints": [
      "test",
      "testDraft"
    ]
  },
  "global": {
    "accounts": [
      "status",
      "session",
      "login",
      "register",
      "setup",
      "logout",
      "update",
      "home",
      "privacy"
    ],
    "campaigns": [
      "list",
      "create",
      "update",
      "join",
      "remove",
      "invite",
      "removalCode",
      "invitationStatus",
      "revokeInvitation",
      "banMember",
      "onboarding",
      "configureOnboarding",
      "claimCharacter",
      "streamerLink",
      "revokeStreamer",
      "rulesets",
      "management",
      "preparation",
      "prepare",
      "references",
      "viewAs",
      "journalHistory",
      "journalRevision",
      "journalTrash"
    ],
    "administration": [
      "status",
      "diagnostics",
      "settings",
      "updateSettings",
      "snapshots",
      "createSnapshot",
      "snapshotAction",
      "previewSnapshot",
      "restoreSnapshot",
      "deleteSnapshot",
      "clonePreview",
      "clone",
      "exportCampaign",
      "importCampaign",
      "updates"
    ],
    "administration.updates": [
      "check",
      "notification",
      "channel",
      "apply"
    ],
    "modules": [
      "list",
      "catalog",
      "catalogLatest",
      "status",
      "install",
      "state",
      "configure",
      "activation",
      "update",
      "removalPreview",
      "remove",
      "defaultMarketplace",
      "configureDefaultMarketplace",
      "acknowledge",
      "localInstallationInfo",
      "installLocal"
    ]
  },
  "local": {
    "i18n": [
      "locale",
      "t",
      "has",
      "number",
      "register",
      "onChange"
    ]
  }
};
