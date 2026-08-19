# Input commands

The Input Registry owns physical input. Keyboards, pointers and gestures are read by the core Input Runtime and nowhere else; a package never installs a listener on the host document, never receives a `KeyboardEvent`, and never sees a DOM node it did not create. What a package registers is a *semantic command*: a named intention with a label, the contexts it belongs to, and the bindings it starts with. What the user owns is which key invokes it.

Registration and invocation both require `input.commands`.

## Two kinds of command

A command may be handled locally, executed on the server, or both.

A **local semantic command** is handled in the browser. Use it when the intention is about the interface — opening a panel, focusing an application, switching a view. Pass a handler as the second argument to `register`:

```js
await sdk.input.commands.register({
  id: "open-console",
  label: "Open console",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+U"]
}, async (invocation) => {
  await sdk.ui.applications.render("console", host);
});
```

The handler receives an `InputCommandInvocationDTO` — `commandId`, `packageId`, `source`, `binding`, `context` — and nothing else. It is resolved metadata, not an event.

A **registered action command** is executed by the server. Use it when the intention changes authoritative state. Name a registered action, and pre-bind the input that action needs:

```js
const actor = await sdk.actors.get(actorId);

await sdk.input.commands.register({
  id: "engage-scanner",
  label: "Engage scanner",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+S"],
  registeredAction: "my-package:scanner.engage@1",
  actionInput: { actorId: actor.id }
});
```

Both may be combined: supply a handler *and* a `registeredAction`, and the handler runs locally while the server executes the action.

## Command invocation metadata is not action input

The metadata describing *how* a command was invoked — which binding, which context — is never passed to the registered action. An action receives only `actionInput`, exactly as recorded at registration.

This matters because `actionInput` is package-definition data, not a runtime payload. It is validated and canonicalised when the command is registered, stored by the core runtime, and used verbatim on every invocation. A caller cannot substitute its own: an invocation that supplies action input for a command that pre-bound its own is rejected outright rather than merged. Commands without `actionInput` still accept caller-supplied input, which the action's own schema validates as usual.

Pre-bound input is bounded plain JSON. There is no expression language, no interpolation and no path syntax — if a command needs to target a resource whose ID is only known at runtime, register the command once that ID exists. Registering the same command id again replaces the definition, including its pre-bound input, so a package may re-register whenever the resource it targets changes.

## Authority

A command grants no authority. A local handler runs with the privileges of ordinary package code: every SDK call it makes derives its principal from the authenticated session and is checked against capabilities and campaign authority exactly as if the user had clicked a button. A registered action command is checked the same way — the caller must be permitted to perform the action, whatever the command definition says.

Nothing in a command definition can forge a user, a campaign, a GM role, an audience or a permission context. Commands are scoped to the campaign they were registered in and are invisible from any other.

## Bindings

`defaultBindings` are what the command starts with. A user's own binding, set through `sdk.input.bindings.set`, replaces the default rather than adding to it, and takes effect immediately — no reload, and the previous key stops working at the same moment.

```js
const bound = await sdk.input.bindings.set("engage-scanner", "Alt+K");
```

A binding is a modifier-prefixed key such as `Alt+K`, `Ctrl+Shift+P` or `F7`. Two rules are enforced by the core:

- **Reserved bindings are refused.** Shortcuts the browser or the application already owns — `Ctrl+L`, `Ctrl+T`, `Ctrl+W`, `Ctrl+N`, `Ctrl+R`, `Ctrl+Shift+T`, `Alt+F4`, `F5`, `F12` — cannot be claimed.
- **Conflicts are refused.** A binding already held by another command, in any package, is rejected rather than silently shadowed.

Bindings belong to the user, not the campaign or the package: one user's choice is invisible to everyone else. A successful change emits `input.binding.changed` to that user, so other surfaces can re-read. A rejected change emits nothing.

Read the current set with `sdk.input.bindings.get()`, and list the commands available to the package with `sdk.input.commands.list()`.

## Contexts and typing suppression

`contexts` declares where a command belongs: `global`, `scene`, `actor-sheet`, `package-application`, `combat`.

Two contexts govern typing. When focus is in a text field, a textarea, a select or a contenteditable region, a command runs only if it declares `text-input`. Declaring `text-input-excluded` refuses invocation while typing even then, and always wins when both are present. A command that declares neither is suppressed while typing.

Suppression is core-owned. A package must never filter keys itself — it has no access to the events required to do so, and any package-side filtering would disagree with the core rules the user sees everywhere else.

## Exactly once

One physical press invokes at most one command. When several commands share a binding the first match claims the press and the rest are skipped; a held key repeating does not re-invoke. A command that is suppressed, unbound or disposed produces no invocation at all rather than a failed one.

## Gestures

`sdk.input.gestures.register` binds a pointer gesture — `tap`, `double-tap`, `long-press`, `drag`, `pan`, `cancel` — to a command id, and accepts the same optional handler. The invocation carries `source: "gesture"` and the gesture name. As with keys, the core owns every pointer listener.

## Lifecycle

Registration returns a disposer. Calling it removes the command immediately: the binding stops resolving, the handler is dropped, and no listener is left behind — the core owns the only listeners there are, so a package cannot leak one.

Disposers are also run when the package unloads. A deactivated package has no registered commands, so its bindings resolve to nothing; re-activating it re-registers them through the normal lifecycle.
