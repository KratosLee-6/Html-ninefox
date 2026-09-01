# Html九尾狐 v0.2.5 · 本地安装与启动

## Windows 最简单方式

1. 确认已安装 **Python 3.10 或更高版本**，安装 Python 时勾选“Add Python to PATH”。
2. 双击项目根目录的 `install-and-run-windows.cmd`。
3. 脚本会在当前目录创建独立环境 `.htmlninefox-venv`，安装 `dist/htmlninefox-0.2.5-py3-none-any.whl`，启动服务并打开浏览器。
4. 浏览器访问：`http://127.0.0.1:8620`。服务窗口关闭后，本地工作台也会停止。

> `.whl` 不是用 WinRAR、应用商店或浏览器直接打开的安装包；它是 Python wheel，需要用 `pip` 安装。双击脚本已经替你完成这些命令。

## Windows 手动安装

在项目目录打开 PowerShell：

```powershell
py -3 -m venv .htmlninefox-venv
.\.htmlninefox-venv\Scripts\Activate.ps1
python -m pip install --upgrade .\dist\htmlninefox-0.2.5-py3-none-any.whl
htmlninefox serve
```

然后打开 `http://127.0.0.1:8620`。

## macOS / Linux

```bash
python3 -m venv .htmlninefox-venv
source .htmlninefox-venv/bin/activate
python -m pip install --upgrade ./dist/htmlninefox-0.2.5-py3-none-any.whl
htmlninefox serve
```

## 安装成桌面应用（PWA）

本地服务启动后，用 Edge 或 Chrome 打开工作台，点击顶部“安装”。它会创建独立窗口和桌面入口，但本地 Python 服务仍需运行。

## 常见问题

- **找不到 Python**：重新安装 Python 3.10+ 并勾选 PATH。
- **PowerShell 禁止激活脚本**：无需激活，直接运行 `.\.htmlninefox-venv\Scripts\python.exe -m htmlninefox.cli serve`。
- **8620 端口被占用**：先关闭旧的 Html九尾狐服务窗口，再重新启动。
- **首次安装较慢**：pip 需要安装 `pyyaml`、`click`、`rich` 等依赖。
