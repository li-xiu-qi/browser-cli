@echo off
chcp 65001 >nul
:: 通义听悟转录工具快速入口

set SCRIPT_DIR=%~dp0
set TONGYI_DIR=%SCRIPT_DIR%tongyi-tingwu

node "%TONGYI_DIR%\core_transcribe.js" %*
