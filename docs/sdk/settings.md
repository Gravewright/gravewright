# Settings

Package settings are declared in `manifest.json` and accessed at runtime through `sdk.settings` or the `sdk.setting` shortcut.

Settings are package-scoped. A package can read and write only its own setting values through the scoped SDK.

## Manifest declaration

```json
"settings": [
  {
    "key": "enabled",
    "scope": "user",
    "type": "boolean",
    "default": true,
    "label": "Enable"
  },
  {
    "key": "dice.color",
    "scope": "user",
    "type": "string",
    "default": "#7c5cff",
    "label": "Die color"
  },
  {
    "key": "theme",
    "scope": "campaign",
    "type": "enum",
    "default": "dark",
    "label": "Theme",
    "options": ["dark", "light"]
  }
]
```

## Setting fields

| Field | Required | Description |
|---|---:|---|
| `key` | Yes | Stable setting key. |
| `scope` | No | `global`, `campaign`, or `user`. Defaults to package/runtime behavior when omitted. |
| `type` | Yes | `boolean`, `string`, `number`, `integer`, or `enum`. |
| `default` | No | Default value. |
| `label` | No | Human-readable label. |
| `options` | Required for `enum` | Allowed enum values. |

## Scopes

| Scope | Use for |
|---|---|
| `global` | Installation-wide operator configuration. |
| `campaign` | Campaign-level package behavior controlled by the GM/operator. |
| `user` | Per-user preferences such as visual toggles or colors. |

## Runtime access

Declare the `settings` capability:

```json
"capabilities": ["settings"]
```

Read definitions:

```js
const definitions = sdk.settings.definitions();
```

Read all current values:

```js
const values = sdk.settings.all();
```

Read a single value:

```js
const enabled = sdk.settings.get("enabled", true);
```

Write a value:

```js
await sdk.settings.set("enabled", false);
```

Write for a specific campaign:

```js
await sdk.settings.set("enabled", true, { campaignId: "campaign-id" });
```

Shortcut:

```js
const enabled = sdk.setting("enabled");
await sdk.setting("enabled", false);
```

## Validation rules

The validator reports `sdk.validation.setting_invalid` when:

- `key` is empty;
- `scope` is not `global`, `campaign`, or `user`;
- `type` is not `boolean`, `string`, `number`, `integer`, or `enum`;
- `type` is `enum` and `options` is missing or empty.

## Best practices

- Use stable keys. Renaming a key is a breaking change for saved settings.
- Prefix keys by feature area, for example `dice.color`, `ui.enabled`, `automation.mode`.
- Use `user` scope for personal display preferences.
- Use `campaign` scope for game behavior that should be shared by table participants.
- Avoid storing secrets in package settings.
- Keep defaults safe and reversible.

## Value coercion and scope (stability)

Declared values are coerced **strictly** to the setting `type`; an unrecognised
value is rejected with the stable code `sdk.settings.invalid_value` instead of
silently becoming a default.

- `boolean` — true: `true`, `"true"`, `"1"`, `"yes"`, `"on"`, `1`; false:
  `false`, `"false"`, `"0"`, `"no"`, `"off"`, `""`, `0`. Anything else is invalid
  (notably, `"false"` never becomes `true`).
- `integer` / `number` — must parse cleanly; booleans and non-numeric strings are
  invalid.
- `enum` — must be one of the declared `options`.

Scope precedence for the effective value is **default → campaign → user**.
`user` scope is **per user, global across campaigns** (keyed by user id, not by
campaign). A stored value that is corrupted JSON falls back to the default at
read time and is reported by the doctor (`setting_value_corrupted`).
