@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 uv。请先安装 uv，或使用 Windows 便携包。
  pause
  exit /b 1
)
uv run htmlninefox app
