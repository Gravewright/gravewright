# HTTP API and Route Groups

Gravewright currently uses browser-oriented HTTP routes rather than a versioned REST API. Routes return templates, redirects, JSON payloads, or files depending on the workflow.

## Auth Routes

```text
GET  /
GET  /login
POST /login
GET  /register
POST /register
POST /logout
GET  /forgot-password
POST /forgot-password
GET  /reset-password
POST /reset-password
```

## Inside Routes

```text
GET  /inside
GET  /inside/invitations/pending
GET  /inside/diagnostics
POST /inside/settings
POST /inside/privacy
POST /inside/admin/users/delete
POST /inside/admin/users/reset-password
```

Inside routes require an authenticated user. Some routes require instance owner privileges.

## Campaign Routes

```text
POST /campaigns
POST /campaigns/update
POST /campaigns/request-delete
POST /campaigns/delete
POST /campaigns/set-system
POST /campaigns/permissions
POST /campaigns/invitations
POST /campaigns/invitations/accept
POST /campaigns/invitations/decline
POST /campaigns/modules/enable
POST /campaigns/modules/disable
```

Campaign mutating routes require membership and usually GM access.

## Game Routes

```text
GET  /game
POST /game/chat
POST /game/chat/delete
POST /game/chat/clear
POST /game/presence/leave
POST /game/preferences/layout
POST /game/settings/table
```

## Scene and Map Routes

```text
POST /game/scenes/group
POST /game/scenes/activate
POST /game/scenes/update
POST /game/scenes/start-point
POST /game/scenes/upload-map
GET  /game/scenes/{scene_id}/edit-modal
GET  /game/scenes/{scene_id}/manifest
GET  /game/scenes/{scene_id}/image
GET  /game/scenes/{scene_id}/layers/{layer_id}/tiles/{tx}/{ty}
GET  /game/scenes/{scene_id}/tokens
```

Scene file routes enforce campaign membership and scene visibility.

## Actor, Item, Journal, and Combat Routes

Actors, items, journals, folders, ownership, sheet data, content imports, resource permissions, and combat use `/game/actor`, `/game/item`, `/game/journal`, `/game/resource-permissions`, and `/game/combat` route groups.

These routes are browser workflow APIs. Treat payload and response shapes as application internals unless documented in a public API guide.

## Systems and Modules

```text
POST /systems/install
POST /systems/enable
POST /systems/disable
POST /systems/remove
GET  /systems/{system_id}/asset/{asset_path}
POST /modules/upload
POST /modules/install
POST /modules/enable
POST /modules/disable
POST /modules/remove
GET  /modules/{module_id}/asset/{asset_path}
POST /modules/settings
```

System and module installation routes require owner privileges. Asset routes serve only validated declared paths.
