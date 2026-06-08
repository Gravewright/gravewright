# Getting Started

## Requirements

- Python 3.11 or newer
- `uv`
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

## Start the App

```bash
uv run uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## First Local Flow

1. Register a local user.
2. Open `/inside`.
3. Create a campaign.
4. Install and enable a system from the Systems tab.
5. Assign the system to the campaign.
6. Open the campaign table.
7. Upload a map from the Scenes panel.
8. Create actors, items, journals, and tokens.

## Local Data

Default runtime files live under:

```text
storage/
```

Default package data lives under:

```text
data/
```

Set `GRAVEWRIGHT_DATA_DIR` if installable systems and modules should live outside the repository.
