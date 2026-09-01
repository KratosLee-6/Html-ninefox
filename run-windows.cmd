@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".htmlninefox-venv\Scripts\htmlninefox.exe" (
  echo 尚未安装，请先双击 install-and-run-windows.cmd
  pause
  exit /b 1
)
".htmlninefox-venv\Scripts\htmlninefox.exe" app
