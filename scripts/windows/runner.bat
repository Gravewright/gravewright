@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Gravewright Runner
set "GW_CODEPAGE="
for /f "tokens=2 delims=:" %%C in ('chcp') do set "GW_CODEPAGE=%%C"
if defined GW_LAUNCHER_CODEPAGE set "GW_CODEPAGE=%GW_LAUNCHER_CODEPAGE%"
chcp 65001 >nul
set "GW_PYTHON=@@PYTHON@@"
set "GW_DATA=@@DATA@@"
set "GW_UV=@@UV@@"
set "GW_NO_PAUSE="
set "GW_NO_BROWSER="
set "GW_CHECK="
set "GW_PORT="
set "GW_PUSHED="
set "GW_EXIT=1"
:arguments
if "%~1"=="" goto start
if /i "%~1"=="--no-pause" goto no_pause
if /i "%~1"=="--no-browser" goto no_browser
if /i "%~1"=="--check" goto check
if /i "%~1"=="--data-dir" goto data
if /i "%~1"=="--port" goto port
echo Unknown argument. Use Install Windows.bat to install or configure.
goto finish
:no_pause
set "GW_NO_PAUSE=1"
shift /1
goto arguments
:no_browser
set "GW_NO_BROWSER=--no-browser"
shift /1
goto arguments
:check
set "GW_CHECK=--check"
shift /1
goto arguments
:data
if "%~2"=="" goto finish
set "GW_DATA=%~2"
shift /1
shift /1
goto arguments
:port
if "%~2"=="" goto finish
set "GW_PORT=%~2"
shift /1
shift /1
goto arguments
:start
if not exist "%GW_PYTHON%" goto missing
pushd "@@PROJECT@@"
if errorlevel 1 goto missing
set "GW_PUSHED=1"
if not exist "@@BOOTSTRAP@@" goto missing
for %%V in (VIRTUAL_ENV PYTHONHOME PYTHONPATH) do set "%%V="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if defined GW_PORT goto with_port
"%GW_PYTHON%" -X utf8 "@@BOOTSTRAP@@" --project "@@PROJECT@@" --data-dir "%GW_DATA%" %GW_NO_BROWSER% %GW_CHECK%
set "GW_EXIT=%errorlevel%"
goto finish
:with_port
"%GW_PYTHON%" -X utf8 "@@BOOTSTRAP@@" --project "@@PROJECT@@" --data-dir "%GW_DATA%" --port "%GW_PORT%" %GW_NO_BROWSER% %GW_CHECK%
set "GW_EXIT=%errorlevel%"
goto finish
:missing
echo Installation is missing. Run Install Windows.bat first.
:finish
if defined GW_PUSHED popd
if not "%GW_EXIT%"=="0" if not defined GW_NO_PAUSE pause
if defined GW_CODEPAGE chcp %GW_CODEPAGE% >nul
exit /b %GW_EXIT%
