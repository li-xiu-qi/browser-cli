@echo off
chcp 65001 >nul
echo ==========================================
echo  百度网盘转录工具安装脚本
echo ==========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    exit /b 1
)

echo [1/3] 创建虚拟环境...
if exist ".venv" (
    echo      虚拟环境已存在，跳过
) else (
    python -m venv .venv
    echo      虚拟环境创建完成
)

echo [2/3] 安装依赖...
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo      依赖安装完成

echo [3/3] 验证安装...
python -c "import requests, click, rich; print('     所有依赖已正确安装')"

echo.
echo ==========================================
echo  安装完成！
echo ==========================================
echo.
echo 使用方法:
echo   .venv\Scripts\python transcribe.py --help
echo.
echo 或先激活虚拟环境:
echo   .venv\Scripts\activate
echo   python transcribe.py --help
echo.

pause
