# Manifest validation

The manifest validator treats package manifests as untrusted input. It parses defensively and reports structured errors and warnings.

Validation returns:

- `errors` — blocking validation failures;
- `warnings` — non-blocking risks or compatibility concerns;
- `compatibility_status` — computed compatibility status for the running Gravewright version;
- `ok` — true when there are no errors.

## Validation coverage

The validator checks:

1. manifest is an object;
2. `schemaVersion` is `1`;
3. `sdkVersion` is `"1"`;
4. `kind` is known;
5. `id` is present and safe;
6. required metadata exists;
7. `authors` and `license` shapes;
8. compatibility declaration exists;
9. capabilities are a list;
10. forbidden capabilities are rejected;
11. unknown capabilities are rejected;
12. activation shape, scope, and mode;
13. kind-specific activation rules;
14. ruleset storage and actor type requirements;
15. assets package restrictions;
16. asset entry ids, labels, paths, duplicates, and extensions;
17. setting keys, scopes, types, and enum options;
18. content pack ids, types, and paths;
19. entrypoints shape;
20. every manifest-referenced path is safe;
21. dependencies and conflicts;
22. distribution type;
23. computed compatibility status.

## Common errors

| Error key | Meaning | Typical fix |
|---|---|---|
| `sdk.validation.not_object` | Manifest is not a JSON object. | Replace with a valid object. |
| `sdk.validation.schema_version` | `schemaVersion` is not `1`. | Set `schemaVersion: 1`. |
| `sdk.validation.sdk_version` | `sdkVersion` is not `"1"`. | Set `sdkVersion: "1"`. |
| `sdk.validation.kind` | Unknown package kind. | Use `ruleset`, `addon`, `library`, `content`, `theme`, or `assets`. |
| `sdk.validation.id_required` | Missing package id. | Add `id`. |
| `sdk.validation.id_invalid` | Package id is unsafe or not kebab-case. | Use lowercase kebab-case and match the package directory name. |
| `sdk.validation.name_required` | Missing package name. | Add `name`. |
| `sdk.validation.version_required` | Missing package version. | Add `version`. |
| `sdk.validation.authors_invalid` | `authors` has invalid shape. | Use an array of strings or objects. |
| `sdk.validation.license_invalid` | `license` is not a string. | Use a string. |
| `sdk.validation.compatibility_required` | No compatibility range declared. | Add `minimum`, `verified`, or `maximum`. |
| `sdk.validation.capabilities_required` | `capabilities` is missing or not a list. | Add `capabilities: []` or a list of capability strings. |
| `sdk.validation.capability_forbidden` | Forbidden capability requested. | Remove backend/raw/override capability. |
| `sdk.validation.capability_unknown` | Capability is not in the allow-list. | Use a documented capability or update the validator/docs together. |
| `sdk.validation.activation_required` | `activation` is missing or invalid. | Add `activation` with a valid `mode`. |
| `sdk.validation.activation_invalid` | Invalid activation scope or mode. | Use documented scope/mode values. |
| `sdk.validation.ruleset_activation_mode` | Ruleset does not use `exclusive`. | Set `activation.mode: "exclusive"`. |
| `sdk.validation.ruleset_storage_required` | Ruleset lacks `provides.storage.model`. | Add storage model. |
| `sdk.validation.ruleset_actor_types_required` | Ruleset has no actor types. | Add at least one `provides.actorTypes` entry. |
| `sdk.validation.addon_activation_mode` | Addon does not use `multiple`. | Set `activation.mode: "multiple"`. |
| `sdk.validation.library_activation_mode` | Library does not use `passive`. | Set `activation.mode: "passive"`. |
| `sdk.validation.assets_activation_mode` | Assets package does not use `multiple`. | Set `activation.mode: "multiple"`. |
| `sdk.validation.assets_invalid_assets` | Invalid assets package shape. | Add valid asset ids/labels/paths and remove game model fields. |
| `sdk.validation.setting_invalid` | Invalid setting definition. | Fix key, scope, type, or enum options. |
| `sdk.validation.content_pack_invalid` | Invalid content pack. | Fix id, type, or path. |
| `sdk.validation.entrypoint_invalid` | `entrypoints` is not an object. | Use an object, even when empty. |
| `sdk.validation.path_unsafe` | Referenced path is unsafe. | Use package-relative paths without `..`, absolute paths, or URLs. |
| `sdk.validation.dependency_invalid` | Dependency id/kind invalid. | Use safe package id and valid kind. |
| `sdk.validation.conflict_invalid` | Conflict id invalid. | Use safe package id. |
| `sdk.validation.distribution_invalid` | Distribution shape/type invalid. | Use `zip`, `git`, or `directory`. |

## Common warnings

| Warning key | Meaning | Typical fix |
|---|---|---|
| `sdk.validation.incompatible` | Package is outside the running version compatibility window. | Update compatibility or use a compatible Gravewright version. |
| `sdk.validation.assets_image_extension` | Image-like asset has an unexpected extension. | Use `.png`, `.jpg`, `.jpeg`, `.webp`, or `.svg`. |
| `sdk.validation.assets_map_extension` | Map asset has an unexpected extension. | Use `.png`, `.jpg`, `.jpeg`, or `.webp`. |
| `sdk.validation.assets_audio_extension` | Audio asset has an unexpected extension. | Use `.mp3`, `.ogg`, or `.wav`. |

## Validation commands

```bash
grave package validate data/packages/my-package
grave package validate data/packages/my-package --json
grave package doctor my-package
grave doctor --packages-dir data/packages
```

## CI recommendation

For package repositories, run validation in CI:

```bash
grave package validate . --json
```

For local SDK packages, run package validation against their directories:

```bash
grave package validate data/packages/rulesets/<your-ruleset>
grave package validate data/packages/addons/<your-addon>
```
