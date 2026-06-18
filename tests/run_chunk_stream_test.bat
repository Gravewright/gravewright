@echo off
setlocal EnableExtensions EnableDelayedExpansion

if /i "%~1"==":stats" goto stats_worker

set "noBuild=0"
set "noSeed=0"
set "keep=0"
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--no-build" (set "noBuild=1"& shift& goto parse_args)
if /i "%~1"=="-NoBuild" (set "noBuild=1"& shift& goto parse_args)
if /i "%~1"=="--no-seed" (set "noSeed=1"& shift& goto parse_args)
if /i "%~1"=="-NoSeed" (set "noSeed=1"& shift& goto parse_args)
if /i "%~1"=="--keep" (set "keep=1"& shift& goto parse_args)
if /i "%~1"=="-Keep" (set "keep=1"& shift& goto parse_args)
echo Unknown argument: %~1 1>&2
exit /b 2

:args_done
for %%I in ("%~dp0.") do set "scriptDir=%%~fI"
for %%I in ("!scriptDir!\..") do set "rootDir=%%~fI"
set "composeFile=!scriptDir!\docker-compose.chunk-stream.yml"
set "baseOutput=!scriptDir!\performance\chunk_stream"
set "dbPath=!rootDir!\storage\gravewright.sqlite3"
for /f %%I in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'))"') do set "runId=%%I"
if not defined runId set "runId=%RANDOM%"
for /f "delims=" %%I in ('python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ'))"') do set "startedAt=%%I"
for /f %%I in ('python -c "import time; print(int(time.time()))"') do set "startEpoch=%%I"
set "outputDir=!baseOutput!\runs\!runId!"
set "latestDir=!baseOutput!\latest"
set "statsFile=!outputDir!\docker_stats.txt"
set "statsStop=!outputDir!\.stop_stats"
set "statsDone=!outputDir!\.stats_done"
set "status=1"
set "appStarted=0"
set "statsStarted=0"
mkdir "!outputDir!" 2>nul

echo.
echo ============================================================
echo  Gravewright - CHUNK STREAM DOCKER TEST
echo  WebSocket binary viewport + reconnect + session.resume
echo  Run ID: !runId!
echo ============================================================
echo [0/6] Preparing output directory...
echo       !outputDir!

if "!noSeed!"=="1" (
  echo [1/6] Skipping seed ^(--no-seed^)
) else (
  echo [1/6] Seeding chunk-stream scene...
  uv run python "!baseOutput!\seed.py" --db "!dbPath!" >"!outputDir!\seed_output.txt" 2>&1
  set "commandExit=!errorlevel!"
  type "!outputDir!\seed_output.txt"
  if not "!commandExit!"=="0" goto failed
)

if "!noBuild!"=="1" (
  echo [2/6] Skipping build ^(--no-build^)
) else (
  echo [2/6] Building Docker image...
  docker compose -f "!composeFile!" build >"!outputDir!\build_output.txt" 2>&1
  set "commandExit=!errorlevel!"
  type "!outputDir!\build_output.txt"
  if not "!commandExit!"=="0" goto failed
)

echo [3/6] Starting app container...
docker compose -f "!composeFile!" up -d app >"!outputDir!\compose_up.txt" 2>&1
set "commandExit=!errorlevel!"
type "!outputDir!\compose_up.txt"
if not "!commandExit!"=="0" goto failed
set "appStarted=1"

echo       Waiting for health check...
set /a attempt=0
:health_loop
docker compose -f "!composeFile!" ps app >"!outputDir!\.health" 2>&1
findstr /i "healthy" "!outputDir!\.health" >nul && goto healthy
set /a attempt+=1
if !attempt! geq 60 (echo App did not become healthy after 120 seconds. 1>&2& goto failed)
timeout /t 2 /nobreak >nul
goto health_loop
:healthy
echo       App is healthy.
for /f "delims=" %%I in ('docker compose -f "!composeFile!" ps -q app') do set "appContainer=%%I"
if not defined appContainer goto failed

echo [4/6] Capturing Docker limits...
docker inspect !appContainer! --format "Name={{.Name}} NanoCpus={{.HostConfig.NanoCpus}} Memory={{.HostConfig.Memory}} MemorySwap={{.HostConfig.MemorySwap}}" >"!outputDir!\docker_limits.txt" 2>&1
type "!outputDir!\docker_limits.txt"

echo [5/6] Sampling resource usage -^> !statsFile!
start "gravewright-chunk-stats" /b cmd /d /c ""%~f0" :stats "!appContainer!" "!statsFile!" "!statsStop!" "!statsDone!""
set "statsStarted=1"

echo [6/6] Running chunk stream reconnect check...
docker compose -f "!composeFile!" run --rm chunk_stream >"!outputDir!\chunk_stream_output.txt" 2>&1
set "status=!errorlevel!"
type "!outputDir!\chunk_stream_output.txt"
goto cleanup

:failed
set "status=1"
:cleanup
echo.
echo [cleanup] Collecting final artifacts...
if "!statsStarted!"=="1" (
  type nul >"!statsStop!"
  call :wait_for_file "!statsDone!" 10
)
if "!appStarted!"=="1" (
  docker compose -f "!composeFile!" ps >"!outputDir!\compose_ps.txt" 2>&1
  docker compose -f "!composeFile!" logs app >"!outputDir!\app_logs.txt" 2>&1
)
if "!appStarted!"=="1" if "!keep!"=="0" docker compose -f "!composeFile!" down --remove-orphans >nul 2>&1
if "!keep!"=="1" echo [cleanup] Keeping containers because --keep was used.
call :write_summary
del /q "!outputDir!\.health" "!statsStop!" "!statsDone!" 2>nul
tar.exe -a -c -f "!outputDir!\chunk_stream_!runId!.zip" -C "!outputDir!" *.txt summary.md 2>nul
if exist "!latestDir!" rmdir /s /q "!latestDir!"
xcopy "!outputDir!" "!latestDir!\" /e /i /q >nul

echo.
if "!status!"=="0" (echo PASS - Gate WS-R1 completed successfully.) else echo FAIL - Gate WS-R1 failed.
echo Results: !outputDir!
echo Latest:  !latestDir!
exit /b !status!

:write_summary
for /f "delims=" %%I in ('python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ'))"') do set "finishedAt=%%I"
for /f %%I in ('python -c "import time; print(int(time.time()))"') do set "finishEpoch=%%I"
set /a duration=finishEpoch-startEpoch
if "!status!"=="0" (set "result=PASS") else set "result=FAIL"
set "gitCommit=unknown"
for /f "delims=" %%I in ('git -C "!rootDir!" rev-parse --short HEAD 2^>nul') do set "gitCommit=%%I"
call :last_line "!outputDir!\chunk_stream_output.txt" "[chunk-stream] OK" "[chunk-stream] OK not found" okLine
call :last_line "!outputDir!\chunk_stream_output.txt" "scene:" "scene:        unknown" sceneLine
call :last_line "!outputDir!\chunk_stream_output.txt" "layer:" "layer:        unknown" layerLine
call :last_line "!outputDir!\chunk_stream_output.txt" "scene_epoch:" "scene_epoch:  unknown" epochLine
call :last_line "!outputDir!\chunk_stream_output.txt" "known_chunks:" "known_chunks: unknown" knownLine
>"!outputDir!\summary.md" (
  echo ```txt
  echo Status:      !result!
  echo Started:     !startedAt!
  echo Finished:    !finishedAt!
  echo Duration:    !duration!s
  echo Git commit:  !gitCommit!
  echo Run ID:      !runId!
  echo ```
  echo.
  echo ```txt
  echo Test:         WebSocket binary viewport + reconnect + session.resume
  echo Compose:      !composeFile!
  echo App limit:    1 CPU / 4 GB
  echo Client limit: 0.5 CPU / 512 MB
  echo ```
  echo.
  echo ```txt
  echo !okLine!
  echo !sceneLine!
  echo !layerLine!
  echo !epochLine!
  echo !knownLine!
  echo ```
)
exit /b 0

:last_line
set "%~4=%~3"
if not exist "%~1" exit /b 0
for /f "delims=" %%I in ('findstr /l /c:"%~2" "%~1"') do set "%~4=%%I"
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
:stats_loop
if exist "!stop!" goto stats_done
docker stats --no-stream --no-trunc --format "{{.Name}}	{{.CPUPerc}}	{{.MemUsage}}	{{.MemPerc}}	{{.NetIO}}	{{.BlockIO}}" "!container!" >>"!output!" 2>&1
timeout /t 2 /nobreak >nul
goto stats_loop

:stats_done
type nul >"!done!"
exit /b 0
