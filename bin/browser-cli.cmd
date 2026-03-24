@echo off
setlocal

where node >nul 2>nul
if errorlevel 1 goto :missing_node

set "ROOT=%~dp0"
set "ENTRY=%ROOT%..\src\cli.js"

if not exist "%ENTRY%" goto :missing_entry

node "%ENTRY%" %*
exit /b %errorlevel%

:missing_node
echo [browser-cli] node not found in PATH
exit /b 1

:missing_entry
echo [browser-cli] local files missing
echo [browser-cli] expected: "%ENTRY%"
exit /b 1
