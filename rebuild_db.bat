@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo.
echo  岩心数字化平台 · 重建数据库
echo  将重建 app\data\core.db、岩心影像，并生成 2017 补充数据表。
echo.

if exist "app\data\core.db" (
  copy /Y "app\data\core.db" "app\data\core.db.bak" >nul
  echo  已备份旧库：app\data\core.db.bak
)

py -3 app\seed.py
if errorlevel 1 (
  echo.
  echo  重建失败：请确认已安装 Python 3 与 Pillow。
  pause
  exit /b 1
)

echo.
echo  数据库已重建完成：app\data\core.db
echo  可双击 start.bat 启动演示。
pause
