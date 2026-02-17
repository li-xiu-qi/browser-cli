@echo off
chcp 65001 >nul
:: 百度网盘转录工具快速启动脚本

set SCRIPT_DIR=%~dp0
call "%SCRIPT_DIR%.venv\Scripts\activate"

:: 检查是否有参数
if "%~1"=="" (
    echo 百度网盘媒体文件转录文稿工具
    echo.
    echo 用法: baidu-trans [命令] [选项]
    echo.
    echo 命令:
    echo   transcribe       获取单个/多个文件转录文稿
    echo   search           搜索并列出音视频文件
    echo   batch            批量转录
    echo.
    echo 示例:
    echo   baidu-trans transcribe --fsid 465930705301366
    echo   baidu-trans search --search "一堂"
    echo   baidu-trans batch --scan-dir "/课程" --output ./output/
    echo.
    exit /b 1
)

set COMMAND=%~1
shift

if "%COMMAND%"=="transcribe" (
    python "%SCRIPT_DIR%transcribe.py" %*
) else if "%COMMAND%"=="search" (
    python "%SCRIPT_DIR%search_and_transcribe.py" %*
) else if "%COMMAND%"=="batch" (
    python "%SCRIPT_DIR%batch_transcribe.py" %*
) else (
    echo 未知命令: %COMMAND%
    echo 可用命令: transcribe, search, batch
    exit /b 1
)
