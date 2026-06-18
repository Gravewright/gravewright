@echo off
call "%~dp0run_locust_performance.bat" table-realistic %*
exit /b %errorlevel%
