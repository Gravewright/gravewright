# Documentation Update Summary

This documentation bundle updates Gravewright docs for the current SDK + CLI architecture.

## Updated Areas

- Root README quick start now uses `grave doctor` and `grave run --open`.
- Alpha warning now emphasizes backup-before-update and short Alpha arcs.
- CLI docs now cover launchers, run, doctor, backup, restore, lock, package lifecycle, campaign activation, and per-kind scaffolding.
- SDK docs now treat packages as the only extension model.
- Package kind docs now align content packages with campaign activation.
- Operations docs now document backup/restore flow through the CLI.
- Testing docs now include CLI parser tests, focused CLI tests, unit suite, compile check, and browser E2E.
- Contributing docs now include CLI/package development expectations.
- Security docs now cover trusted JavaScript packages, SDK capabilities, and package path safety.
- Brazilian Portuguese docs now mirror the updated operational model.

## Recommended Verification

```bash
grave doctor
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```
