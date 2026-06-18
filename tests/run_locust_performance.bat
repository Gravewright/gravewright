@echo off
setlocal EnableExtensions EnableDelayedExpansion

if /i "%~1"==":stats" goto stats_worker

set "scenario=%~1"
if not defined scenario goto usage
shift

set "noBuild=0"
set "noSeed=0"
set "allowFailure=0"
set "cleanVolumes=0"
set "keepApp=0"
set "statsInterval=2"
set "readinessTimeout=300"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--no-build" (set "noBuild=1"& shift& goto parse_args)
if /i "%~1"=="-NoBuild" (set "noBuild=1"& shift& goto parse_args)
if /i "%~1"=="--no-seed" (set "noSeed=1"& shift& goto parse_args)
if /i "%~1"=="-NoSeed" (set "noSeed=1"& shift& goto parse_args)
if /i "%~1"=="--allow-failure" (set "allowFailure=1"& shift& goto parse_args)
if /i "%~1"=="-AllowFailure" (set "allowFailure=1"& shift& goto parse_args)
if /i "%~1"=="--clean-volumes" (set "cleanVolumes=1"& shift& goto parse_args)
if /i "%~1"=="-CleanVolumes" (set "cleanVolumes=1"& shift& goto parse_args)
if /i "%~1"=="--keep-app" (set "keepApp=1"& shift& goto parse_args)
if /i "%~1"=="-KeepApp" (set "keepApp=1"& shift& goto parse_args)
if /i "%~1"=="--stats-interval" (set "statsInterval=%~2"& shift& shift& goto parse_args)
if /i "%~1"=="--readiness-timeout" (set "readinessTimeout=%~2"& shift& shift& goto parse_args)
echo Unknown argument: %~1 1>&2
exit /b 2

:args_done
if /i "%scenario%"=="perf" (
  set "composeName=docker-compose.perf.yml"
  set "outputName=performance"
  set "seedName=performance\seed.py"
  set "description=20 users / spawn 2/s / 90s"
  set "resources=1 CPU / 4 GB"
  set "role=baseline"
) else if /i "%scenario%"=="max-stress" (
  set "composeName=docker-compose.max-stress.yml"
  set "outputName=performance\max_stress"
  set "seedName=performance\max_stress\seed.py"
  set "description=500 users / spawn 20/s / 300s"
  set "resources=1 CPU / 4 GB"
  set "role=breaking-point"
) else if /i "%scenario%"=="i5-stress" (
  set "composeName=docker-compose.i5-stress.yml"
  set "outputName=performance\i5_stress"
  set "seedName=performance\i5_stress\seed.py"
  set "description=500 users / spawn 20/s / 300s"
  set "resources=6 CPUs / 8 GB / 1 worker"
  set "role=vertical-headroom"
) else if /i "%scenario%"=="table-realistic" (
  set "composeName=docker-compose.table-realistic.yml"
  set "outputName=performance\table_realistic"
  set "seedName=performance\table_realistic\seed.py"
  set "description=15 users / 3 tables / realistic session"
  set "resources=1 CPU / 4 GB / 1 worker"
  set "role=product-acceptance"
) else goto usage

for %%I in ("%~dp0.") do set "scriptDir=%%~fI"
for %%I in ("!scriptDir!\..") do set "rootDir=%%~fI"
set "composeFile=!scriptDir!\!composeName!"
set "seedFile=!scriptDir!\!seedName!"
set "dbPath=!rootDir!\storage\gravewright.sqlite3"
for /f %%I in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d-%%H%%M%%S'))"') do set "timestamp=%%I"
if not defined timestamp set "timestamp=%RANDOM%"
set "outputDir=!rootDir!\!outputName!\!timestamp!"
set "locustOutput=!outputDir!\locust.log"
set "statsOutput=!outputDir!\docker_stats.tsv"
set "metadataOutput=!outputDir!\metadata.json"
set "statsStop=!outputDir!\.stop_stats"
set "statsDone=!outputDir!\.stats_done"

if not exist "!composeFile!" (echo Compose file not found: !composeFile! 1>&2& exit /b 1)
if "!noSeed!"=="0" if not exist "!seedFile!" (echo Seed file not found: !seedFile! 1>&2& exit /b 1)
mkdir "!outputDir!" 2>nul

for /f "delims=" %%I in ('git -C "!rootDir!" rev-parse HEAD 2^>nul') do set "gitCommit=%%I"
if not defined gitCommit set "gitCommit=null"
for /f "delims=" %%I in ('python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())"') do set "startedAt=%%I"
set "jsonRoot=!rootDir:\=\\!"
set "jsonScript=!scriptDir:\=\\!"
set "jsonCompose=!composeFile:\=\\!"
set "jsonSeed=!seedFile:\=\\!"
set "jsonDb=!dbPath:\=\\!"
set "jsonNoBuild=false"
set "jsonNoSeed=false"
set "jsonAllowFailure=false"
set "jsonCleanVolumes=false"
set "jsonKeepApp=false"
if "!noBuild!"=="1" set "jsonNoBuild=true"
if "!noSeed!"=="1" set "jsonNoSeed=true"
if "!allowFailure!"=="1" set "jsonAllowFailure=true"
if "!cleanVolumes!"=="1" set "jsonCleanVolumes=true"
if "!keepApp!"=="1" set "jsonKeepApp=true"
>"!metadataOutput!" (
  echo {
  echo   "scenario": "!scenario!", "role": "!role!",
  echo   "description": "!description!", "resources": "!resources!",
  echo   "startedAt": "!startedAt!", "rootDir": "!jsonRoot!",
  echo   "scriptDir": "!jsonScript!", "composeFile": "!jsonCompose!",
  if "!noSeed!"=="1" (echo   "seedFile": null,) else echo   "seedFile": "!jsonSeed!",
  echo   "sqlitePath": "!jsonDb!", "noBuild": !jsonNoBuild!, "noSeed": !jsonNoSeed!,
  echo   "allowFailure": !jsonAllowFailure!, "cleanVolumes": !jsonCleanVolumes!, "keepApp": !jsonKeepApp!,
  echo   "statsIntervalSeconds": !statsInterval!, "readinessTimeoutSeconds": !readinessTimeout!,
  if "!gitCommit!"=="null" (echo   "gitCommit": null, "runner": "cmd.exe") else echo   "gitCommit": "!gitCommit!", "runner": "cmd.exe"
  echo }
)

echo Scenario:    !scenario!
echo Description: !description!
echo Resources:   !resources!
echo Compose:     !composeFile!
echo Output:      !outputDir!

set "appStarted=0"
set "statsStarted=0"
set "locustExit=0"
call :section "Checking Docker"
docker info >nul 2>&1 || (echo Docker is not ready. Start Docker Desktop and enable Linux containers. 1>&2& goto fail)

if "!cleanVolumes!"=="1" (
  call :section "Cleaning compose stack and volumes"
  docker compose -f "!composeFile!" down -v --remove-orphans || goto fail
)
if "!noSeed!"=="0" (
  call :section "Seeding database"
  python "!seedFile!" --db "!dbPath!" || goto fail
) else call :section "Skipping seed"
if "!noBuild!"=="0" (
  call :section "Building containers"
  docker compose -f "!composeFile!" build || goto fail
) else call :section "Skipping build"

call :section "Starting app"
docker compose -f "!composeFile!" up -d app || goto fail
set "appStarted=1"

call :section "Waiting for app HTTP readiness"
set "appPort=8000"
for /f "tokens=2 delims=:" %%I in ('docker compose -f "!composeFile!" port app 8000 2^>nul') do set "appPort=%%I"
set /a waitCount=0
:readiness_loop
docker compose -f "!composeFile!" ps -a app >"!outputDir!\.app_state" 2>&1 || goto fail
findstr /i "Exit Exited" "!outputDir!\.app_state" >nul && (
  echo App container exited before becoming ready. 1>&2
  docker compose -f "!composeFile!" logs --tail=300 app
  goto fail
)
findstr /i "healthy" "!outputDir!\.app_state" >nul && goto ready
curl.exe -f -s -o NUL --max-time 2 "http://localhost:!appPort!/" && goto ready
set /a waitCount+=1
if !waitCount! geq !readinessTimeout! (
  echo App did not become HTTP-ready within !readinessTimeout! seconds. 1>&2
  docker compose -f "!composeFile!" logs --tail=300 app
  goto fail
)
timeout /t 1 /nobreak >nul
goto readiness_loop

:ready
echo App ready: http://localhost:!appPort!/
for /f "delims=" %%I in ('docker compose -f "!composeFile!" ps -q app') do set "appContainer=%%I"
if not defined appContainer goto fail
call :section "Starting docker stats capture"
start "gravewright-stats" /b cmd /d /c ""%~f0" :stats "!appContainer!" "!statsOutput!" "!statsStop!" "!statsDone!" !statsInterval!"
set "statsStarted=1"

call :section "Running Locust"
docker compose -f "!composeFile!" run --rm locust >"!locustOutput!" 2>&1
set "locustExit=!errorlevel!"
type "!locustOutput!"
if not "!locustExit!"=="0" if "!allowFailure!"=="0" goto fail_locust
call :section "Done"
echo Results: !outputDir!
goto cleanup_success

:fail_locust
echo Locust failed with exit code !locustExit!. Use --allow-failure for exploratory tests. 1>&2
goto cleanup_failure
:fail
set "locustExit=1"
:cleanup_failure
set "finalExit=!locustExit!"
if "!finalExit!"=="0" set "finalExit=1"
goto cleanup
:cleanup_success
set "finalExit=0"
:cleanup
if "!statsStarted!"=="1" (
  type nul >"!statsStop!"
  call :wait_for_file "!statsDone!" 10
)
if "!appStarted!"=="1" if "!keepApp!"=="0" (
  call :section "Stopping compose stack"
  if "!cleanVolumes!"=="1" (docker compose -f "!composeFile!" down -v --remove-orphans) else docker compose -f "!composeFile!" down --remove-orphans
)
if "!keepApp!"=="1" echo Keeping app container running because --keep-app was set.
del /q "!outputDir!\.app_state" "!statsStop!" "!statsDone!" 2>nul
exit /b !finalExit!

:section
echo.
echo ==^> %~1
exit /b 0

:wait_for_file
set /a waitWorker=0
:wait_for_file_loop
if exist "%~1" exit /b 0
set /a waitWorker+=1
if !waitWorker! geq %~2 exit /b 1
timeout /t 1 /nobreak >nul
goto wait_for_file_loop

:stats_worker
setlocal EnableDelayedExpansion
set "container=%~2"
set "output=%~3"
set "stop=%~4"
set "done=%~5"
set "interval=%~6"
>"!output!" echo timestamp	name	cpu	mem_usage	mem_perc	net_io	block_io
:stats_loop
if exist "!stop!" goto stats_done
for /f "delims=" %%I in ('python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())"') do set "now=%%I"
for /f "delims=" %%I in ('docker stats --no-stream --format "{{.Name}}	{{.CPUPerc}}	{{.MemUsage}}	{{.MemPerc}}	{{.NetIO}}	{{.BlockIO}}" "!container!" 2^>^&1') do >>"!output!" echo !now!	%%I
timeout /t !interval! /nobreak >nul
goto stats_loop

:stats_done
type nul >"!done!"
exit /b 0

:usage
echo Usage: %~nx0 ^<perf^|max-stress^|i5-stress^|table-realistic^> [options] 1>&2
exit /b 2
