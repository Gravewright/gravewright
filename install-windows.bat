@echo off
setlocal enableextensions
title Gravewright fallback launcher
cd /d "%~dp0"

echo ===========================================================
echo   Gravewright fallback launcher
echo ===========================================================
echo(

if exist "%~dp0Gravewright.exe" (
  echo Starting the recommended Gravewright.exe launcher...
  "%~dp0Gravewright.exe"
  exit /b %errorlevel%
)

echo Gravewright.exe was not found. Running the transitional debug fallback.
echo This fallback does not install uv automatically.
echo(

where uv >nul 2>nul
if errorlevel 1 if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: uv is missing.
  echo Download the complete official Windows ZIP again or install uv from:
  echo https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)

uv sync --frozen || goto :fail
uv run python scripts/setup_local_env.py || goto :fail
uv run python -m app.cli doctor
uv run python -m app.cli run --open || goto :fail
exit /b 0

:fail
echo(
echo ERROR: Gravewright setup or startup did not finish.
echo Copy the output above when asking for help.
pause
exit /b 1
