@echo off
chcp 65001 >nul
:: 百度网盘转录工具快速入口

set SCRIPT_DIR=%~dp0
set BAIDU_DIR=%SCRIPT_DIR%baidu-pan

:: 激活虚拟环境并执行
call "%BAIDU_DIR%\.venv\Scripts\activate" 2>nul
python "%BAIDU_DIR%\transcribe.py" %*
