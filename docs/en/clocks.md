# Progress clocks

[Documentation](../README.md) · [Português (Brasil)](../pt-BR/clocks.md) · [Campaign management](campaign-management.md)

Progress clocks track tasks, threats, countdowns and other campaign goals with
filled segments. They belong to the campaign and work with every game system.
The table and the GM's campaign manager edit the same saved records.

## Create and configure

On the table, open **Clocks** in the menu bar. Before entering play, open
**Manage campaign** and select **Clocks**. A campaign GM can create a clock,
choose its name and color, and set its current progress.

Choose a preset with 4, 6, 8, 10 or 12 segments, or **Custom** for an integer
between 2 and 24. Progress stays between zero and the number of segments.
A campaign can contain up to 128 clocks.

Choose the clock's scope:

| Scope | Where it appears |
| --- | --- |
| Campaign | In that campaign across scenes |
| Current scene | Only when viewing the associated scene |

Selecting a scene context in the campaign manager prepares that scene's clocks.
It preserves the table's broadcast, each participant's private scene selection
and table presence. Entering the tabletop remains a separate action.
Deleting a scene also removes clocks associated with that scene.

## Audience and controls

| Setting or role | Behavior |
| --- | --- |
| GM only | The server sends the clock only to campaign GMs |
| Players | Participants viewing its scope can see the clock |
| Players can advance this clock | Players can advance or reduce progress on that public clock |
| GM | Can configure, advance, reset and delete clocks |
| Streamer | Can view permitted clocks with read-only controls |
| Pinned | Displays the permitted clock in the table's pinned-clock area |

Player editing changes progress. Configuration, visibility, scene scope,
resetting and deletion remain GM operations. Hiding a control is a presentation
choice; the server checks the participant's current membership and permission
on every request. Private clocks and clocks belonging to another viewed scene
are filtered before delivery.

Use the increase and decrease controls to change progress, **Reset** to return
to zero, or the GM editor to revise a clock's configuration. Closing the clock
window leaves saved clocks intact. Reloading the page restores saved progress.
Pinned clocks use the same authorized records as the full list.

## Synchronization and integration

The tabletop receives committed clock changes through its existing realtime
connection. Campaign management uses HTTP, refreshing on focus and through its
normal periodic refresh. **Refresh campaign** retrieves current state immediately.

Concurrent edits use the saved version. If a clock changes while an operation
is pending, refresh its current state and review the action. Each logical write
uses a new request UUID; retrying that exact operation reuses its UUID so it is
applied once.

Browser integrations use the `clocks` domain of the
[public API](api.md): `state`, `create`, `update`, `advance`, `reset` and `delete`.
Changes to an existing clock provide its `id` and integer `version`; advancing
also provides `delta`. Create and update accept the native fields `name`, `segments`,
`value`, `color`, `visibility`, `playersCanEdit`, `pinned` and `scopeSceneId`.
Visibility is `gm` or `players`; `scopeSceneId: null` selects campaign scope.
The request's `sceneId` supplies the current viewing context. Returned clocks
expose their saved scope as `clock.sceneId`.
Integrations retain the same campaign, scene and role checks as the native UI.

The clock faces are native SVG artwork. No external VTT module or game-system
package is required.

## MapBuilder mechanisms

The Smart Object **Control clock** node connects a mechanism's event to an
advance, reduce, set or reset operation. It accepts a configured amount or a
connected numeric input. Changes use the same saved clock and update permitted
table windows and pinned displays after commit.

A GM-authored node authorizes its specific clock operation when a participant
interacts with that mechanism. This includes private clocks and clocks whose
direct player editing is disabled. It does not grant general clock access or
expose private names and values. The runtime requires an active campaign GM.
Clock scope still restricts which scene may execute the binding.

See [Control progress clocks in MapBuilder](map-builder.md#control-progress-clocks)
for connections, amount limits and safe simulation/rehearsal workflows.

## Backups and upgrading

Campaign exports, snapshots, restores and clones preserve clock configuration,
progress and campaign or scene scope. Clone options can omit all clocks with
`clocks: false`. Omitting scenes with `scenes: false` also omits scene-scoped
clocks while preserving campaign clocks when clocks are included.

This feature adds the `gravewright_table` migration `0003_progress_clock`.
Apply pending migrations before restarting an existing installation:

```bash
uv run --locked python manage.py migrate
```
