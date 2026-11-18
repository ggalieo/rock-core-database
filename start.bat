@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
  echo 服务已在运行：http://127.0.0.1:8010
  start "" http://127.0.0.1:8010
  exit /b 0
)

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  set PY=py -3
) else (
  set PY=python
)

if not exist "app\data\core.db" (
  echo 首次运行：正在生成演示数据库与岩心影像，请稍候...
  %PY% app\seed.py
  if errorlevel 1 (
    echo 数据生成失败，请确认已安装 Python 3 与 Pillow。
    pause
    exit /b 1
  )
)

echo.
echo  岩心数字化平台 · 初版演示
echo  地址：http://127.0.0.1:8010
echo  按 Ctrl+C 停止服务
echo.
start "" http://127.0.0.1:8010
%PY% app\server.py --port 8010
pause
