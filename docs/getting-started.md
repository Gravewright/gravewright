# Getting Started

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A browser with modern JavaScript support

SQLite is used by default for local development.

## Install Dependencies

```bash
uv sync
```

## Configure Local Environment

```bash
cp .env.example .env
```

The default `.env.example` is suitable for local development. Change `SESSION_SECRET` before using any shared or public instance.

## Run Diagnostics

```bash
chmod +x grave
./grave doctor
```

Fallback:

```bash
uv run python -m app.cli doctor
```

## Start the App

```bash
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli run --open
```

Open:

```text
http://127.0.0.1:8000
```

Windows:

```bat
grave.bat doctor
grave.bat run --open
```

## First Local Flow

1. Register a local user.
2. Open `/inside`.
3. Create a campaign.
4. Check package availability:

   ```bash
   ./grave package list
   ```

5. Install and enable a ruleset package if needed:

   ```bash
   ./grave package install dnd5e --yes --enable
   ```

6. Assign the ruleset to the campaign from the UI or package activation flow.
7. Open the campaign table.
8. Upload a map from the Scenes panel.
9. Create actors, items, journals, and tokens.

## Back Up Before Updating

Before updating Gravewright or changing packages on a table you care about:

```bash
./grave doctor
./grave backup -o gravewright-backup.zip --include-assets --verify
```

Test restore on a copy before updating real data.

## Local Data

Default runtime files live under:

```text
storage/
```

Default package data lives under:

```text
data/packages/
```

Set `GRAVEWRIGHT_DATA_DIR` if installable SDK packages should live outside the repository.
