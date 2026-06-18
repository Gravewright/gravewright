@echo off
call "%~dp0run_locust_performance.bat" i5-stress %*
exit /b %errorlevel%
