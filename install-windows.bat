@echo off
rem ===========================================================================
rem  Gravewright - one-click setup and launch for Windows.
rem
rem  Double-click this file. It installs everything it needs the first time
rem  (no admin required), then starts Gravewright and opens your browser.
rem  Run it again any time to start playing again.
rem ===========================================================================
setlocal enableextensions
title Gravewright

rem Always work from the folder this script lives in (the project root).
cd /d "%~dp0"

echo(
echo ===========================================================
echo   Gravewright - setup and launch (Windows)
echo ===========================================================
echo(

rem --- 1) Make sure uv (the installer/runtime manager) is available ----------
where uv >nul 2>nul
if errorlevel 1 (
  echo [1/5] Installing uv ^(one-time^)...
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
  rem uv installs for the current user; make it usable in this same window.
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
  echo [1/5] uv is already installed.
)

where uv >nul 2>nul
if errorlevel 1 (
  echo(
  echo ERROR  uv could not be installed automatically.
  echo        Close this window, open a new one, and double-click this file again.
  echo        If it still fails, install uv from https://docs.astral.sh/uv/ and retry.
  goto :fail
)

rem --- 2) Install the matching Python + all dependencies ---------------------
echo [2/5] Installing Gravewright and its dependencies ^(first run can take a few minutes^)...
call uv sync --frozen
if errorlevel 1 goto :fail

rem --- 3) and 4) Create local configuration + a unique session secret --------
echo [3/5] Preparing local configuration...
call uv run python scripts/setup_local_env.py
if errorlevel 1 goto :fail

rem --- 5) Quick health check, then start the server --------------------------
echo [4/5] Checking the installation...
call uv run python -m app.cli doctor

echo(
echo [5/5] Starting Gravewright.
echo        Your browser will open at http://127.0.0.1:8000
echo        Keep this window open while you play. Close it or press Ctrl+C to stop.
echo(
call uv run python -m app.cli run --open
goto :end

:fail
echo(
echo Setup did not finish. Please copy the messages above when asking for help.
echo(
pause
exit /b 1

:end
echo(
echo Gravewright has stopped. You can close this window.
pause
endlocal
