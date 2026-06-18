@echo off
call "%~dp0run_locust_performance.bat" max-stress %*
exit /b %errorlevel%
