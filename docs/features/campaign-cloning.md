# Selective campaign cloning

Campaign GMs can create an independent campaign from selected parts of an
existing campaign. The clone wizard on the campaign list provides a read-only
preview before creation.

The selectable groups are packages, scenes, actors, items, journals, and
campaign/role settings. Folder trees and journal quest-board relationships are
remapped to new identifiers. The operation uses one database transaction, so a
failure does not leave a partial campaign.

The source campaign is never modified. Members, invitations, join codes, chat,
presence, audit data, streamer links, user-specific permissions, and physical
assets are deliberately excluded. Actor and item image references are cleared;
scenes retain their structural records but not uploaded tiles or images.

Set `CAMPAIGN_CLONE_ENABLED=false` to hide the wizard and disable both clone
endpoints without deleting existing campaigns.
