@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "WHEEL=dist\htmlninefox-0.3.0b2-py3-none-any.whl"
set "VENV=.htmlninefox-venv"

if not exist "%WHEEL%" (
  echo [错误] 未找到 %WHEEL%
  pause
  exit /b 1
)

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [错误] 未找到 Python 3.10+。请先安装 Python，并勾选 Add Python to PATH。
    pause
    exit /b 1
  )
  set "PYTHON_CMD=python"
)

if not exist "%VENV%\Scripts\python.exe" (
  echo [1/3] 创建独立 Python 环境...
  %PYTHON_CMD% -m venv "%VENV%"
  if errorlevel 1 goto :failed
)

echo [2/3] 安装 Html九尾狐 v0.3.0b2...
"%VENV%\Scripts\python.exe" -m pip install --upgrade "%WHEEL%"
if errorlevel 1 goto :failed

echo [3/3] 启动工作台 http://127.0.0.1:8620
"%VENV%\Scripts\htmlninefox.exe" app
exit /b 0

:failed
echo.
echo [失败] 安装未完成，请查看上方错误，或阅读 docs\INSTALL.md。
pause
exit /b 1
