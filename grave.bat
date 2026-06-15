@echo off
rem Gravewright local CLI launcher.
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR  uv was not found on PATH.
  echo FIX    Install uv: https://docs.astral.sh/uv/
  exit /b 4
)

uv run python -m app.cli %*
exit /b %ERRORLEVEL%
