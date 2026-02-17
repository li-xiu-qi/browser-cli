@echo off
chcp 65001 >nul
:: 音视频转录文稿工具 - Windows 快速入口

set SCRIPT_DIR=%~dp0

:: 检查是否有参数
if "%~1"=="" (
    echo ==========================================
    echo    音视频转录文稿工具
    echo ==========================================
    echo.
    echo 用法: transcribe [文件路径] [选项]
    echo.
    echo 选项:
    echo   --provider baidu^|tongyi^|auto   选择平台（默认自动）
    echo   --output, -o [目录]            输出目录
    echo   --analyze-only                 仅分析文件
    echo   --list-providers               列出支持的平台
    echo.
    echo 示例:
    echo   transcribe "./我的视频.mp4"
    echo   transcribe "./我的视频.mp4" --provider tongyi
    echo   transcribe "./我的视频.mp4" --provider baidu --fsid 123456
    echo.
    echo 子工具:
    echo   transcribe-baidu      百度网盘转录工具
    echo   transcribe-tongyi     通义听悟转录工具
    echo.
    exit /b 1
)

:: 调用主脚本
python "%SCRIPT_DIR%transcribe.py" %*
