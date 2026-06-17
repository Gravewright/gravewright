# Creating Packages With AI

Gravewright is designed so package authors can describe a game system or extension in natural language, let the CLI generate a safe scaffold, and use `grave package doctor` to keep the package inside the SDK contract.

## The Loop

1. Scaffold a package.
2. Ask an AI assistant to edit only that package directory.
3. Validate the package.
4. Paste doctor output back into the AI assistant.
5. Repeat until `grave package doctor` is clean.

## Ruleset Example

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
```

Prompt:

```text
You are editing a Gravewright SDK v1 ruleset package.

Only edit files inside data/packages/rulesets/my-rpg.
Do not edit Gravewright core.
Do not invent capabilities.
Prefer declarative schemas, sheets, rules, mappings, content packs, and locales.
After each change, the package must pass:

grave package validate data/packages/rulesets/my-rpg
grave package doctor my-rpg
```

## Addon Example

```bash
grave addon new my-addon --name "My Addon" --js --settings
```

Prompt:

```text
You are editing a Gravewright SDK v1 addon package.

Only edit files inside data/packages/addons/my-addon.
Use window.GravewrightSDK.register({ id, setup, ready }).
Only call SDK APIs allowed by the declared capabilities.
Do not access raw database, raw filesystem, backend internals, or undocumented globals.
```

## Fixing Doctor Output

When doctor reports errors, paste the output into the assistant:

```bash
grave package doctor my-rpg --json
```

Prompt:

```text
Here is the Gravewright package doctor output.
Explain what is wrong, then provide a minimal patch.
Only change package files.
Do not change Gravewright core.
Do not invent capabilities.
```

## Safety Rules

- Do not upload `.env`, database files, private maps, or private campaign content to external AI tools.
- Do not ask an AI assistant to bypass validator errors.
- Do not use copyrighted or commercial game content unless you have rights to distribute it.
- Treat packages with `assets.scripts` as trusted JavaScript.
- Run `grave backup` before applying package changes to a table you care about.
