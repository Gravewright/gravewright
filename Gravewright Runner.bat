@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Gravewright Runner - Alpha 0.1.0
rem Native CMD launcher: tool discovery, downloads, installation and startup.
rem CALL uses fixed labels only. Never pass paths through CALL's second parse.
rem Delayed expansion stays disabled to preserve exclamation marks in paths.
set "GW_EXIT=1"
set "GW_CHECK="
set "GW_NO_BROWSER="
set "GW_NO_PAUSE="
set "GW_DATA="
set "GW_PORT="
set "GW_WORK="
set "GW_WORK_CREATED="
set "GW_PUSHED="
set "GW_CODEPAGE="
set "GW_ERROR="

:arguments
if "%~1"=="" goto start
if /i "%~1"=="--help" goto help
if /i "%~1"=="--check" goto argument_check
if /i "%~1"=="--no-browser" goto argument_browser
if /i "%~1"=="--no-pause" goto argument_pause
if /i "%~1"=="--data-dir" goto argument_data
if /i "%~1"=="--port" goto argument_port
set "GW_ERROR=Unknown argument. Run Gravewright Runner.bat --help for usage."
goto failed
:argument_check
set "GW_CHECK=--check"
shift /1
goto arguments
:argument_browser
set "GW_NO_BROWSER=--no-browser"
shift /1
goto arguments
:argument_pause
set "GW_NO_PAUSE=1"
shift /1
goto arguments
:argument_data
if "%~2"=="" goto missing_argument
for %%D in ("%~2\.") do set "GW_DATA=%%~fD"
shift /1
shift /1
goto arguments
:argument_port
if "%~2"=="" goto missing_argument
set "GW_PORT=%~2"
shift /1
shift /1
goto arguments
:missing_argument
set "GW_ERROR=The option needs a value. Run Gravewright Runner.bat --help for usage."
goto failed

:start
echo Gravewright Runner - Alpha 0.1.0
echo.
set "GW_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "GW_ARCH=%PROCESSOR_ARCHITEW6432%"
set "GW_ERROR=This Runner requires Windows 10 1803 or newer, or Windows 11, on x64."
if /i not "%GW_ARCH%"=="AMD64" goto failed
if not defined LOCALAPPDATA goto failed
rem Windows supplies these utilities even when Python and Node are absent.
set "GW_SYSTEM=%SystemRoot%\System32"
if not exist "%GW_SYSTEM%\curl.exe" goto failed
if not exist "%GW_SYSTEM%\tar.exe" goto failed
if not exist "%GW_SYSTEM%\certutil.exe" goto failed
for /f "tokens=2 delims=:" %%C in ('chcp') do set "GW_CODEPAGE=%%C"
chcp 65001 >nul
set "GW_ERROR=Cannot open the project folder. Extract the ZIP to a writable folder."
pushd "%~dp0"
if errorlevel 1 goto failed
set "GW_PUSHED=1"
set "GRAVEWRIGHT_ROOT=%CD%"
set "GW_ERROR=The project is incomplete. Extract the entire ZIP before starting."
for %%F in (pyproject.toml uv.lock scripts\gravewright_runner.py scripts\prepare_frontend.py gravewright\maps\frontend\package.json gravewright\maps\frontend\package-lock.json gravewright\maps\scripts\build.cjs) do if not exist "%%F" goto failed
set "GW_RUNTIME=%LOCALAPPDATA%\Gravewright\runner"
set "GW_ERROR=Cannot create the Runner working directory under LOCALAPPDATA."
if not exist "%GW_RUNTIME%" mkdir "%GW_RUNTIME%"
set "GW_WORK=%GW_RUNTIME%\work-%RANDOM%-%RANDOM%"
mkdir "%GW_WORK%" 2>nul
if errorlevel 1 goto failed
set "GW_WORK_CREATED=1"

rem Settings apply only to this CMD process and its children.
for %%V in (VIRTUAL_ENV PYTHONHOME PYTHONPATH UV_PROJECT UV_PYTHON UV_SYSTEM_PYTHON UV_MANAGED_PYTHON UV_NO_MANAGED_PYTHON UV_PYTHON_NO_REGISTRY UV_FROZEN UV_NO_SYNC UV_WORKING_DIR UV_CONFIG_FILE) do set "%%V="
set "UV_CACHE_DIR=%GW_RUNTIME%\cache"
set "UV_PYTHON_DOWNLOADS=automatic"
set "UV_LINK_MODE=copy"
set "UV_NO_ENV_FILE=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

rem CMD holds handle 9 exclusively until preparation returns. A second launch
rem cannot replace shared runtimes or frontend packages during this interval.
rem The OS releases the handle on termination; the empty lock file may remain.
set "GW_PREPARED="
set "GW_ERROR=Another Runner is preparing an installation. Wait for it to finish and try again."
(call :prepare_application) 9>"%GW_RUNTIME%\prepare.lock"
if not defined GW_PREPARED goto failed
goto start_application

:prepare_application
echo [1/6] Checking uv...
set "GW_ERROR=Could not prepare uv. Check the download or version error above."
call :resolve_uv
if errorlevel 1 exit /b 1
echo Using uv: "%GW_UV%"
"%GW_UV%" --version

echo.
echo [2/6] Checking Python 3.14 x64...
set "GW_ERROR=Could not prepare Python 3.14. Check your connection and the error above."
call :resolve_python
if errorlevel 1 exit /b 1
echo Using Python: "%GW_BASE_PYTHON%"
"%GW_BASE_PYTHON%" --version
rem Preserve the source-location identifier used by previous environments.
"%GW_BASE_PYTHON%" -c "import hashlib,os; print(hashlib.sha256(os.path.abspath(os.environ['GRAVEWRIGHT_ROOT']).upper().encode('utf-8')).hexdigest()[:20])" >"%GW_WORK%\checkout.txt"
if errorlevel 1 exit /b 1
set "GW_CHECKOUT="
set /p "GW_CHECKOUT=" <"%GW_WORK%\checkout.txt"
if not defined GW_CHECKOUT exit /b 1
set "UV_PROJECT_ENVIRONMENT=%GW_RUNTIME%\environments\%GW_CHECKOUT%"
set "GW_FRONTEND_STATE=%GW_RUNTIME%\frontend\%GW_CHECKOUT%"

echo.
echo [3/6] Checking Node.js and npm...
set "GW_ERROR=Could not prepare Node.js and npm. Check the download or version error above."
call :resolve_node
if errorlevel 1 exit /b 1
echo Using Node.js: "%GW_NODE%"
"%GW_NODE%" --version
echo Using npm: "%GW_NPM%"
"%GW_NODE%" "%GW_NPM%" --version
for %%D in ("%GW_NODE%") do set "PATH=%%~dpD;%PATH%"

echo.
echo [4/6] Installing/checking locked Python dependencies...
set "GW_ERROR=Python dependency installation failed. Check the error above and your connection."
"%GW_UV%" --no-config sync --project "%GRAVEWRIGHT_ROOT%" --locked --no-dev --no-python-downloads --python "%GW_BASE_PYTHON%"
if errorlevel 1 exit /b 1
set "GW_PYTHON=%UV_PROJECT_ENVIRONMENT%\Scripts\python.exe"
if not exist "%GW_PYTHON%" exit /b 1

echo.
echo [5/6] Checking npm dependencies and frontend assets...
set "GW_ERROR=Frontend preparation failed. Check the npm/build error and folder permissions."
rem The helper only checks packages/hashes or records a completed build here.
rem The actual npm installation and build commands are executed by this BAT.
set "npm_config_global=false"
set "npm_config_update_notifier=false"
set "npm_config_script_shell=%GW_SYSTEM%\cmd.exe"
"%GW_PYTHON%" -X utf8 scripts\prepare_frontend.py --plan --node "%GW_NODE%" --npm-cli "%GW_NPM%" --state-dir "%GW_FRONTEND_STATE%"
set "GW_PLAN=%errorlevel%"
if "%GW_PLAN%"=="0" goto frontend_ready
if "%GW_PLAN%"=="11" goto build_frontend
if not "%GW_PLAN%"=="10" exit /b 1
echo Installing locked frontend dependencies with npm ci...
"%GW_NODE%" "%GW_NPM%" --prefix "%GRAVEWRIGHT_ROOT%\gravewright\maps\frontend" ci --include=dev --include=optional --no-audit --no-fund
if errorlevel 1 exit /b 1
:build_frontend
echo Building frontend assets with npm run build...
set "GRAVEWRIGHT_BUILD_MANIFEST=%GW_FRONTEND_STATE%\build-outputs.json"
"%GW_NODE%" "%GW_NPM%" --prefix "%GRAVEWRIGHT_ROOT%\gravewright\maps\frontend" run build
if errorlevel 1 exit /b 1
"%GW_PYTHON%" -X utf8 scripts\prepare_frontend.py --record --node "%GW_NODE%" --npm-cli "%GW_NPM%" --state-dir "%GW_FRONTEND_STATE%"
if errorlevel 1 exit /b 1
:frontend_ready
if not exist scripts\windows\create_shortcut.py goto preparation_done
"%GW_PYTHON%" -X utf8 scripts\windows\create_shortcut.py --project-root "%GRAVEWRIGHT_ROOT%"
if errorlevel 1 echo The icon shortcut could not be created. The BAT still works.

:preparation_done
set "GW_PREPARED=1"
exit /b 0

:start_application
echo.
echo [6/6] Preparing the database and starting Gravewright...
echo Keep this window open. Press Ctrl+C here to stop the server.
set "GW_ERROR=Gravewright could not start. See the application error above."
if not defined GW_DATA set "GW_DATA=%LOCALAPPDATA%\Gravewright\data"
if defined GW_PORT goto start_with_port
"%GW_PYTHON%" -X utf8 scripts\gravewright_runner.py --data-dir "%GW_DATA%" %GW_CHECK% %GW_NO_BROWSER%
set "GW_EXIT=%errorlevel%"
goto application_finished
:start_with_port
"%GW_PYTHON%" -X utf8 scripts\gravewright_runner.py --data-dir "%GW_DATA%" --port "%GW_PORT%" %GW_CHECK% %GW_NO_BROWSER%
set "GW_EXIT=%errorlevel%"
:application_finished
if not "%GW_EXIT%"=="0" goto failed
goto finish

:resolve_uv
set "GW_UV="
"%GW_SYSTEM%\where.exe" uv.exe >"%GW_WORK%\uv-candidates.txt" 2>nul
for /f "usebackq delims=" %%U in ("%GW_WORK%\uv-candidates.txt") do (
    set "GW_CANDIDATE=%%U"
    call :try_uv
)
if defined GW_UV exit /b 0
set "GW_CANDIDATE=%GW_RUNTIME%\uv\0.12.13-x64\uv.exe"
set "GW_HASH_FILE=%GW_CANDIDATE%"
set "GW_EXPECTED=e43cc6ca110540ad845ad6aa1e468e224813eb1da76e145413a262d7073d05e7"
call :verify_hash
if errorlevel 1 goto download_uv
call :try_uv
if defined GW_UV exit /b 0
:download_uv
echo No compatible uv found. Downloading uv 0.12.13...
set "GW_URL=https://github.com/astral-sh/uv/releases/download/0.12.13/uv-x86_64-pc-windows-msvc.zip"
set "GW_ARCHIVE=%GW_WORK%\uv.zip"
set "GW_EXPECTED=a86c9dc7bad9b03f388583b7187c05fe9951c2e0d392217e8fd43d97787f6ec2"
call :download
if errorlevel 1 exit /b 1
echo Extracting the verified uv archive...
mkdir "%GW_WORK%\uv"
"%GW_SYSTEM%\tar.exe" -xf "%GW_ARCHIVE%" -C "%GW_WORK%\uv"
if errorlevel 1 exit /b 1
set "GW_HASH_FILE=%GW_WORK%\uv\uv.exe"
set "GW_EXPECTED=e43cc6ca110540ad845ad6aa1e468e224813eb1da76e145413a262d7073d05e7"
call :verify_hash
if errorlevel 1 exit /b 1
if not exist "%GW_RUNTIME%\uv\0.12.13-x64" mkdir "%GW_RUNTIME%\uv\0.12.13-x64"
echo Installing the verified uv executable...
copy /y "%GW_HASH_FILE%" "%GW_CANDIDATE%" >nul
if errorlevel 1 exit /b 1
call :try_uv
if not defined GW_UV exit /b 1
exit /b 0

:try_uv
if defined GW_UV exit /b 0
"%GW_CANDIDATE%" --version >"%GW_WORK%\uv-version.txt" 2>&1
if errorlevel 1 goto uv_probe_failed
rem Rust tools write LF on Windows too. Parse tokens instead of FINDSTR /X,
rem whose end-of-line matching depends on CRLF in the captured output.
set "GW_VERSION="
for /f "usebackq tokens=1,2" %%U in ("%GW_WORK%\uv-version.txt") do if "%%U"=="uv" set "GW_VERSION=%%V"
if not defined GW_VERSION goto uv_probe_failed
for /f "delims=0123456789." %%V in ("%GW_VERSION%") do goto uv_probe_failed
set "GW_MAJOR="
set "GW_MINOR="
set "GW_PATCH="
for /f "tokens=1,2,3 delims=." %%A in ("%GW_VERSION%") do (
    set "GW_MAJOR=%%A"
    set "GW_MINOR=%%B"
    set "GW_PATCH=%%C"
)
if not "%GW_VERSION%"=="%GW_MAJOR%.%GW_MINOR%.%GW_PATCH%" goto uv_probe_failed
if %GW_MAJOR% GTR 0 goto uv_compatible
if %GW_MINOR% LSS 12 exit /b 1
:uv_compatible
set "GW_UV=%GW_CANDIDATE%"
exit /b 0
:uv_probe_failed
echo Could not read a compatible uv version from "%GW_CANDIDATE%".
type "%GW_WORK%\uv-version.txt"
exit /b 1

:resolve_python
set "GW_BASE_PYTHON="
set "UV_PYTHON_PREFERENCE=system"
call :find_python
if defined GW_BASE_PYTHON exit /b 0
set "UV_PYTHON_INSTALL_DIR=%GW_RUNTIME%\python"
set "UV_PYTHON_BIN_DIR=%GW_RUNTIME%\python-bin"
set "UV_PYTHON_INSTALL_BIN=0"
set "UV_PYTHON_INSTALL_REGISTRY=0"
set "UV_PYTHON_NO_REGISTRY=1"
set "UV_PYTHON_PREFERENCE=only-managed"
call :find_python
if defined GW_BASE_PYTHON exit /b 0
echo Python 3.14 was not found. Installing a private copy...
"%GW_UV%" --no-config python install cpython-3.14+gil-windows-x86_64-none
if errorlevel 1 exit /b 1
call :find_python
if not defined GW_BASE_PYTHON exit /b 1
exit /b 0
:find_python
"%GW_UV%" --no-config python find --system --no-project --no-python-downloads cpython-3.14+gil-windows-x86_64-none >"%GW_WORK%\python.txt" 2>nul
if errorlevel 1 exit /b 1
set /p "GW_BASE_PYTHON=" <"%GW_WORK%\python.txt"
if exist "%GW_BASE_PYTHON%" exit /b 0
set "GW_BASE_PYTHON="
exit /b 1

:resolve_node
set "GW_NODE="
set "GW_NPM="
"%GW_SYSTEM%\where.exe" node.exe >"%GW_WORK%\node-candidates.txt" 2>nul
"%GW_SYSTEM%\where.exe" npm.cmd >"%GW_WORK%\npm-candidates.txt" 2>nul
for /f "usebackq delims=" %%N in ("%GW_WORK%\node-candidates.txt") do (
    set "GW_NODE_CANDIDATE=%%N"
    call :try_node
)
if defined GW_NODE exit /b 0
set "GW_NODE_CANDIDATE=%GW_RUNTIME%\node\24.19.0-x64\node.exe"
set "GW_HASH_FILE=%GW_NODE_CANDIDATE%"
set "GW_EXPECTED=3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237"
call :verify_hash
if errorlevel 1 goto download_node
call :try_node
if defined GW_NODE exit /b 0
:download_node
echo No compatible Node.js 22/24 with npm 10 or newer found. Downloading Node.js 24.19.0 and npm...
set "GW_URL=https://nodejs.org/download/release/v24.19.0/node-v24.19.0-win-x64.zip"
set "GW_ARCHIVE=%GW_WORK%\node.zip"
set "GW_EXPECTED=57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73"
call :download
if errorlevel 1 exit /b 1
"%GW_SYSTEM%\tar.exe" -xf "%GW_ARCHIVE%" -C "%GW_WORK%"
if errorlevel 1 exit /b 1
set "GW_HASH_FILE=%GW_WORK%\node-v24.19.0-win-x64\node.exe"
set "GW_EXPECTED=3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237"
call :verify_hash
if errorlevel 1 exit /b 1
if not exist "%GW_RUNTIME%\node\24.19.0-x64" mkdir "%GW_RUNTIME%\node\24.19.0-x64"
rem Keep the complete official distribution, including npm and license files.
"%GW_SYSTEM%\xcopy.exe" "%GW_WORK%\node-v24.19.0-win-x64\*" "%GW_RUNTIME%\node\24.19.0-x64" /e /i /q /y >nul
if errorlevel 1 exit /b 1
set "GW_NODE_CANDIDATE=%GW_RUNTIME%\node\24.19.0-x64\node.exe"
call :try_node
if not defined GW_NODE exit /b 1
exit /b 0

:try_node
if defined GW_NODE exit /b 0
"%GW_NODE_CANDIDATE%" --version >"%GW_WORK%\node-version.txt" 2>nul
if errorlevel 1 exit /b 1
"%GW_BASE_PYTHON%" -c "import pathlib,re,sys; sys.exit(not re.fullmatch(r'v(?:22|24)\.\d+\.\d+\s*', pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')))" "%GW_WORK%\node-version.txt"
if errorlevel 1 exit /b 1
"%GW_NODE_CANDIDATE%" -p process.arch >"%GW_WORK%\node-arch.txt" 2>nul
if errorlevel 1 exit /b 1
set "GW_NODE_ARCH="
set /p "GW_NODE_ARCH=" <"%GW_WORK%\node-arch.txt"
if not "%GW_NODE_ARCH%"=="x64" exit /b 1
rem Version managers may expose a shim. Ask Node for its real installation.
"%GW_NODE_CANDIDATE%" -p process.execPath >"%GW_WORK%\node-path.txt" 2>nul
if errorlevel 1 exit /b 1
set "GW_NODE_REAL="
set /p "GW_NODE_REAL=" <"%GW_WORK%\node-path.txt"
if not exist "%GW_NODE_REAL%" exit /b 1
for %%D in ("%GW_NODE_REAL%") do set "GW_NPM_CANDIDATE=%%~dpDnode_modules\npm\bin\npm-cli.js"
call :try_npm
if defined GW_NODE exit /b 0
for /f "usebackq delims=" %%N in ("%GW_WORK%\npm-candidates.txt") do (
    set "GW_NPM_WRAPPER=%%N"
    call :try_path_npm
)
if defined GW_NODE exit /b 0
exit /b 1
:try_path_npm
if defined GW_NODE exit /b 0
for %%D in ("%GW_NPM_WRAPPER%") do set "GW_NPM_CANDIDATE=%%~dpDnode_modules\npm\bin\npm-cli.js"
call :try_npm
exit /b
:try_npm
if not exist "%GW_NPM_CANDIDATE%" exit /b 1
rem Invoke npm's JS CLI directly, avoiding a second CMD parse by npm.cmd.
"%GW_NODE_REAL%" "%GW_NPM_CANDIDATE%" --version >"%GW_WORK%\npm-version.txt" 2>nul
if errorlevel 1 exit /b 1
"%GW_BASE_PYTHON%" -c "import pathlib,re,sys; v=pathlib.Path(sys.argv[1]).read_text(encoding='utf-8').strip(); sys.exit(not(re.fullmatch(r'\d+\.\d+\.\d+',v) and int(v.split('.')[0])>=10))" "%GW_WORK%\npm-version.txt"
if errorlevel 1 exit /b 1
set "GW_NODE=%GW_NODE_REAL%"
set "GW_NPM=%GW_NPM_CANDIDATE%"
exit /b 0

:download
"%GW_SYSTEM%\curl.exe" --fail --location --retry 2 --connect-timeout 20 --max-time 300 --proto "=https" --tlsv1.2 --output "%GW_ARCHIVE%" "%GW_URL%"
if errorlevel 1 exit /b 1
set "GW_HASH_FILE=%GW_ARCHIVE%"
call :verify_hash
if not errorlevel 1 exit /b 0
echo Download failed its SHA256 check. It will not be extracted or executed.
exit /b 1
:verify_hash
if not exist "%GW_HASH_FILE%" exit /b 1
"%GW_SYSTEM%\certutil.exe" -hashfile "%GW_HASH_FILE%" SHA256 >"%GW_WORK%\sha256.txt" 2>nul
if errorlevel 1 exit /b 1
set "GW_HASH="
for /f "usebackq skip=1 tokens=*" %%H in ("%GW_WORK%\sha256.txt") do if not defined GW_HASH set "GW_HASH=%%H"
set "GW_HASH=%GW_HASH: =%"
if /i "%GW_HASH%"=="%GW_EXPECTED%" exit /b 0
exit /b 1

:help
echo Gravewright Runner - Alpha 0.1.0
echo Usage: "Gravewright Runner.bat" [--check] [--no-browser] [--data-dir PATH] [--port NUMBER] [--no-pause]
echo.
echo --check prepares tools, dependencies, frontend and database, then exits.
echo --no-browser starts the server without opening a browser.
echo --data-dir selects a separate folder for configuration and campaigns.
echo --port overrides the saved port for this run.
echo --no-pause exits immediately on error, for terminals and automation.
set "GW_EXIT=0"
goto finish
:failed
echo.
echo Gravewright Runner: %GW_ERROR%
if "%GW_EXIT%"=="0" set "GW_EXIT=1"
if not defined GW_NO_PAUSE pause
:finish
if defined GW_WORK_CREATED if exist "%GW_WORK%" rmdir /s /q "%GW_WORK%"
if defined GW_PUSHED popd
if defined GW_CODEPAGE chcp %GW_CODEPAGE% >nul
exit /b %GW_EXIT%
