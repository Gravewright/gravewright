@echo off
call "%~dp0run_locust_performance.bat" perf %*
exit /b %errorlevel%
