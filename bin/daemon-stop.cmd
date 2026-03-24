@echo off
setlocal

set "ROOT=%~dp0"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=54000"

call "%ROOT%browser-cli.cmd" stop --port %PORT%
exit /b %errorlevel%
