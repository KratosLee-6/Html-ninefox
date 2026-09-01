# Html九尾狐 v0.3.0 Beta 2 · 安装与运行

## 推荐顺序

1. **Windows 普通用户**：下载并解压 Windows 便携 ZIP，双击 `HtmlNineFox.exe`，无需 Python。
2. **Linux 桌面用户**：给 `.run` 文件执行权限后运行，安装到当前用户目录。
3. **开发者**：在源码目录运行 `uv run htmlninefox app`。
4. **服务器 / NAS**：使用 `docker compose up --build`。

## Windows 便携包

文件：`release/HtmlNineFox-Windows-x64-0.3.0b2.zip`

解压后双击 `HtmlNineFox.exe` 或 `启动Html九尾狐.cmd`。

- 内置 Python 运行时和全部基础依赖。
- 不写注册表，不要求管理员权限。
- 数据、配置和生成结果位于包体旁的 `user-data/`。
- 关闭控制台窗口即可停止服务。

## Windows Setup 安装器

构建定义：`packaging/windows/HtmlNineFox.iss`。安装器会安装到当前用户的 Local AppData，并创建开始菜单和可选桌面快捷方式。正式公开发布前还需要进行代码签名，未签名 Beta 可能触发 SmartScreen 提示。

## Linux 自解压安装包

文件：`release/HtmlNineFox-Linux-0.3.0b2.run`

```bash
chmod +x HtmlNineFox-Linux-0.3.0b2.run
./HtmlNineFox-Linux-0.3.0b2.run
```

安装位置：

- 程序环境：`~/.local/share/htmlninefox/`
- 命令：`~/.local/bin/htmlninefox-app`
- 桌面入口：`~/.local/share/applications/htmlninefox.desktop`

只安装不启动：

```bash
./HtmlNineFox-Linux-0.3.0b2.run --no-launch
```

## Python wheel

```bash
python -m pip install htmlninefox-0.3.0b2-py3-none-any.whl
htmlninefox app
```

## 一键启动命令

`htmlninefox app` 会：

1. 检查 8620 端口。
2. 端口占用时自动尝试 8621、8622 等。
3. 启动本地服务。
4. 等待 `/api/health` 就绪。
5. 自动打开浏览器。

更多方案见 `docs/RUNNING-OPTIONS.md`。
