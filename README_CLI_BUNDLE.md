# Gravewright Complete CLI Bundle

This bundle documents the local CLI wiring.

## Files

```text
grave
grave.bat
install-local-launcher.sh
app/cli/__init__.py
app/cli/__main__.py
app/cli/doctor.py
app/cli/run.py
app/cli/backup.py
app/cli/packages.py
app/cli/scaffold.py
app/cli/exit_codes.py
app/cli/lockfile.py
tests/unit/test_cli_parser_smoke.py
```

## Apply

Extract at the Gravewright repository root.

Then run:

```bash
chmod +x grave install-local-launcher.sh
uv sync --group dev
./grave doctor
./grave package list
./grave run --open
uv run pytest tests/unit/test_cli_parser_smoke.py -q
```

## Windows

```bat
grave.bat doctor
grave.bat run --open
```

## Notes

The root launchers call:

```bash
uv run python -m app.cli
```

so they do not depend on the `grave` console-script entrypoint already being installed.
