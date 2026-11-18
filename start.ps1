$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) {
  Write-Host "服务已在运行：http://127.0.0.1:8010" -ForegroundColor Yellow
  Start-Process "http://127.0.0.1:8010"
  return
}

$py = "python"
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  $py = "py"
  $pyArgs = @("-3")
}

if (-not (Test-Path "app\data\core.db")) {
  Write-Host "首次运行：正在生成演示数据库与岩心影像，请稍候..." -ForegroundColor Cyan
  & $py @pyArgs app\seed.py
  if ($LASTEXITCODE -ne 0) { throw "数据生成失败，请确认已安装 Python 3 与 Pillow。" }
}

Write-Host ""
Write-Host " 岩心数字化平台 · 初版演示" -ForegroundColor Cyan
Write-Host " 地址：http://127.0.0.1:8010" -ForegroundColor Green
Write-Host " 按 Ctrl+C 停止服务"
Write-Host ""

Start-Process "http://127.0.0.1:8010"
& $py @pyArgs app\server.py --port 8010
