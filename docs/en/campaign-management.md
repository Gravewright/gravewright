# Manage a campaign

[Documentation](../README.md) · [Português (Brasil)](../pt-BR/campaign-management.md) · [User guide](user-guide.md)

Use **Manage campaign** on a campaign card or its cover preview to prepare
campaign content before entering the tabletop. The link opens
`/campaigns/<campaign-uuid>/manage` for the selected campaign.

Access follows the current campaign membership. Every campaign GM can use it,
including a co-GM whose account has the participant role. A host owner who is
only a player in that campaign receives no management access. Players, streamers
and nonmembers cannot use this GM workspace. Changing or revoking membership
takes effect on subsequent authorized requests.

## Content tools

The management area uses the campaign's existing documents and native editors.
There is no second campaign copy to merge back into the table.

| Area | What to prepare |
| --- | --- |
| Journals and quests | Diaries, pages, quests, quest boards and roll tables in the native journal editors, with their normal attachments and access rules |
| Characters and PDF sheets | Campaign actors and system sheets; in the PDF System, PDF selection, manual fields, saved rolls, calculations and reusable mappings |
| Items | Item documents and forms supplied by the campaign's installed system |
| Scenes and MapBuilder | Campaign scenes, editable map projects and compatible existing scenes; generating or updating a scene remains an explicit operation |
| File library | Campaign images, PDFs and audio through the native upload, folder and file tools |
| Audio | Tracks, playlists and the campaign's supported audio configuration |
| Cards | Native decks, card artwork and permitted deck operations |
| Compendiums | Authorized campaign and installed content, using the existing catalog and document tools |
| Members and permissions | Invitations, current participants and the native document, folder and page access editors |

In **Participants**, **Invite players** creates an invitation valid for 24 hours
with a maximum of 10 uses. The native modal displays the read-only code;
**Copy code** copies it to the clipboard when selected.

**Remove participant** opens a native confirmation modal identifying the person
before submitting the removal. The campaign service rechecks the caller's GM
membership and refuses removal of another GM or the caller's own membership.

Journals and quests use the same document models and editors as the game.
The management area does not introduce a separate note format or quest system.
GM-only diary pages and private documents retain their existing audience rules.
Opening a document or assigning it to a quest does not grant players permission
to read its private contents.

Character sheets opened from the actor directory edit the campaign actor.
Independent token snapshots retain their own state and native synchronization
rules. PDF layout changes remain GM operations; character values still follow
the sheet's permissions. Item types and game rules belong to the installed
system, so a system without item types does not gain an item catalog here.

See the [MapBuilder guide](map-builder.md) for adoption, linked sources and scene
updates, and [Universal VTT](universal-vtt.md) for import limits and warnings.

## Preparing content and entering play

Opening management does not start the tabletop canvas, Pixi renderer, game
WebSocket connection or table presence. You can organize content without
joining the live scene. **Enter table** remains a separate action.

Saves change the shared campaign records. Explicit commands such as playback,
broadcasting a scene or drawing cards retain their native effects and permissions;
use them when you intend to change that campaign state. Merely opening management
does not execute those commands.

Keep the normal save and conflict workflow. Each new logical mutation uses a new
request UUID; a retry of the same operation reuses its UUID. Revisions detect
concurrent editing. If a document changed elsewhere, reload current state and
review the edit rather than replacing its expected revision silently. Native
editors keep their pending-save, closing and disposal behavior.

## Authorization and integration

The server rechecks campaign membership, GM access and resource ownership.
Hidden buttons are not the authorization boundary. A management URL or a known
asset ID does not authorize access to another campaign. Content delivered to
players and streamers remains filtered by the corresponding native services.

The Inside page adds `can_manage` to its presentation rows using current
memberships; the public campaign JSON format is unchanged. Management tools reuse
the public browser API and native domain services instead of writing documents
directly or creating separate stores. See the [API reference](api.md) for
revisions, receipts, file transfers and system-owned capabilities.
