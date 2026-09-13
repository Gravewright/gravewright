# Testing

[Documentation](../README.md) · [Português](../pt-BR/testing.md)

Run commands from the source root after `uv sync --locked`. The repository uses Django/unittest for Python, Node's built-in runner for JavaScript and standalone Playwright scripts for browser flows. There is no root `npm test` or configured pytest runner.

## Controlled local environment

Tests load the project's `.env` unless a process variable overrides it. For local HTTP browser tests, use a shell with these settings rather than inheriting a production HTTPS origin or external Redis:

```bash
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost,[::1],testserver'
export GRAVEWRIGHT_PUBLIC_ORIGIN=''
export DJANGO_SECURE_COOKIES=false
export GRAVEWRIGHT_REDIS_URL=''
export TRUSTED_PROXIES=''
export GRAVEWRIGHT_MARKETPLACE_URL=''
export GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=''
export GRAVEWRIGHT_RELEASES_REPOSITORY=''
```

These are shell-local settings, not changes to `.env`. Browser fixtures normally override the database and media with temporary directories. Tests may override individual settings as part of a scenario.

## Python

```bash
uv run --locked python manage.py check
uv run --locked python manage.py makemigrations --check --dry-run
uv run --locked python manage.py test config gravewright --noinput
```

The runner uses the explicit file-backed `data/test-gravewright.sqlite3` database to exercise SQLite locking. `--noinput` authorizes replacing that test database if it already exists. Do not point it at valuable data or run parallel suites against the same path. Changing `GRAVEWRIGHT_DATABASE` does not change this explicit test database name. Media-writing tests generally create temporary storage; use a disposable `GRAVEWRIGHT_MEDIA_ROOT` for an extra boundary when running the full suite.

Focused examples:

```bash
uv run --locked python manage.py test config gravewright.accounts gravewright.realtime --noinput
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.modules --noinput
uv run --locked python manage.py test gravewright.dice --noinput
```

## JavaScript

Use a current Node.js release with native ES modules and `node:test`; these commands were checked with Node 24. No root package installation is needed for these tests.

```bash
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

For all colocated JavaScript tests as well, this Python launcher avoids shell-specific recursive globs:

```bash
uv run --locked python - <<'PY'
from pathlib import Path
import subprocess
files = sorted(str(p) for base in ('gravewright', 'tests')
               for p in Path(base).rglob('*')
               if p.name.endswith(('.test.js', '.test.mjs')))
subprocess.run(['node', '--test', *files], check=True)
PY
```

Coverage includes module lifetimes and contracts, shader parsing, board input, tile scheduling, visibility, walls, selection, token routes and PDF field mapping. Pure geometry/model tests do not replace checking the actual GPU-rendered board.

## Browser scenarios

```bash
uv run --locked playwright install chromium
uv run --locked python tests/e2e/authentication.py
uv run --locked python tests/e2e/realtime.py
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/https.py
uv run --locked python tests/e2e/runner.py
```

On Linux, Playwright may need system browser libraries; `uv run --locked playwright install --with-deps chromium` also installs those and can require administrator privileges. Scenarios launch their own servers on temporary ports and seed synthetic data. Most use development settings and write diagnostics under `test-results/`; the HTTPS and runner scenarios use dedicated settings described below. Run scenarios sequentially: several share `test-results/migration-closure/`.

| Change | Relevant scenarios |
| --- | --- |
| Accounts and campaigns | `authentication.py`, `inside.py`, `campaign_controls.py` |
| Realtime and permissions | `realtime.py`, `lighting_realtime.py`, `map_prefetch.py` |
| HTTPS, WSS and proxy trust | `https.py`; Django tests in `config` and `gravewright.realtime` |
| Local Windows runner | `runner.py`; Django tests in `config.test_runner` and `config.test_frontend_preparation`; Windows CMD runner workflow |
| Board, tokens and PDF sheets | `maps.py`, `tokens_pdf.py`, `token_routes.py`, `mixed_selection.py` |
| Effects and rendering | `effects.py`, `effect_editor.py`, `effect_pixels.py`, `light_rendering.py` |
| Journals and dice | `journals.py`, `journal_types.py`, `dice.py`, `dice_validation.py` |
| SDK and table modules | `frontend_api.py`, `table_modules.py`, `management.py`, `marketplace.py` |
| Audio and chat | `audio_lifecycle.py`, `chat_controls.py` |

Some scenarios accept `--original /path/to/reference` for optional pixel comparisons against another checkout's `dist/frontend`. That checkout is not needed for ordinary smoke tests. `reference_tokens.cjs` is an auxiliary comparison tool, not part of the root Node unit command.

[`tests/e2e/https.py`](../../tests/e2e/https.py) runs the installed Daphne with direct TLS and behind a temporary TLS proxy. It checks browser account setup, Secure `__Host-` cookies, HSTS, CSRF rejection, authenticated WSS join/chat and page reload. Raw TLS handshakes check rejection of missing, foreign, HTTP and wrong-port WebSocket origins. The scenario generates temporary certificates and uses isolated database/media paths, production security settings, a test-only static handler and an in-memory channel layer. It needs the locked Python dependencies and Playwright Chromium above; no external Redis or Nginx is required. It leaves the system certificate store and application data untouched and writes diagnostics to `test-results/https/`. This tests the application transport contract; verify your deployed Nginx configuration and certificate separately using the [deployment guide](deployment.md).

`tests/e2e/realtime_processes.py` specifically starts a temporary `redis:7-alpine` Docker container and two ASGI processes. It requires Docker access and network/image availability; it cleans up its own container. It is separate from the default Django/Node suites.

## Windows runner validation

[`tests/e2e/runner.py`](../../tests/e2e/runner.py) starts the actual Python runner with temporary personal data and no Redis. It checks first-time setup, collected static assets, HTTP security, authenticated messages between two WebSocket sessions, occupied-port rejection and restart persistence of the configuration, session, campaign, chat and media. It also checks that the source `.env` and existing development data remain unchanged. The scenario needs the development dependencies and Playwright Chromium above; ordinary runner startup does not.

[`config/test_frontend_preparation.py`](../../config/test_frontend_preparation.py) covers dependency reuse/installation, source and output changes, missing packages or a broken esbuild executable, failed-build retries, corrupt state and concurrent preparation. It also checks the batch `--plan`/`--record` handoff, incomplete dependencies and invalid manifests without running npm installation/build in those helper modes. These controlled subprocess tests belong to the normal Django suite and do not replace an actual npm build. Run the focused suite with `uv run --locked python manage.py test config.test_frontend_preparation --noinput`.

The [Windows workflow](../../.github/workflows/windows-runner.yml) uses CMD to run [`tests/windows/runner.py`](../../tests/windows/runner.py). On any operating system, its source check verifies that obsolete launcher scripts and references are absent:

```sh
python tests/windows/runner.py --source-check
```

On Windows, run the complete native scenario from the source root:

```bat
python tests\windows\runner.py
```

The scenario creates a temporary checkout with spaces, punctuation and Unicode in its path, hides uv and Node/npm from the child process's `PATH`, and runs the actual BAT to install missing tools and prepare the application. Python can still be discovered in the registry or shared installations and reused. It then exposes the installed tools and repeats offline, checking that tools, dependencies and an unchanged frontend build are reused. It reads the icon shortcut back through Windows COM, checks an invalid port fails without pausing, and verifies preservation of the source `.env`, `.venv`, Python/npm locks, personal configuration and user/machine/parent-process `PATH`. Generated frontend outputs are intentionally prepared in the disposable checkout.

The same scenario runs the frontend preparation unit tests and the real Python server scenario in Chromium. `--skip-browser` omits installation of the browser-test dependencies and the browser scenario while keeping the batch checks. Diagnostics are saved under `test-results/windows-runner/`. The temporary source, environment and campaign data are cleaned up when the scenario finishes.

Use `"Gravewright Runner.bat" --check --no-pause --data-dir "<temporary-data-directory>"` for a manual batch preparation check that exits without serving requests. This still installs missing dependencies, builds assets when needed and applies migrations. Workflow presence does not mean its jobs have already passed for a release; `--source-check` alone does not validate native batch execution.

Before publishing a Windows build, run that workflow and check a normal double-click launch, automatic browser opening, Ctrl+C and closing the console on a Windows computer. The [runner guide](windows-runner.md) describes diagnostic mode with an isolated data directory. Tests run on Linux or another operating system verify the Python runtime there, not native Windows CMD or shortcut behavior.

When reporting results, name the commands, versions and failures. A browser scenario that could not launch is not a passing test.
