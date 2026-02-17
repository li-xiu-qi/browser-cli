@echo off
chcp 65001 >nul
:: 百度网盘文件上传快速入口

set SCRIPT_DIR=%~dp0
call "%SCRIPT_DIR%.venv\Scripts\activate" 2>nul

python "%SCRIPT_DIR%\upload.py" %*
