@echo off
setlocal

set "ROOT=%~dp0"
set "ENTRY=%ROOT%..\src\cli.js"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=54000"

where node >nul 2>nul
if errorlevel 1 goto :missing_node

if not exist "%ENTRY%" goto :missing_entry

start "" /b node "%ENTRY%" serve --port %PORT%
echo [browser-cli] daemon launch requested on http://127.0.0.1:%PORT%
exit /b 0

:missing_node
echo [browser-cli] node not found in PATH
exit /b 1

:missing_entry
echo [browser-cli] local files missing
echo [browser-cli] expected: "%ENTRY%"
exit /b 1
