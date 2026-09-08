# Html九尾狐 Linux 用户级安装包

- 不需要 sudo，不修改系统 Python。
- 支持 Linux x86_64 / aarch64 与 Python 3.10–3.13。
- 离线依赖位于 `wheels/`，包含两种架构的 Playwright 驱动依赖；安装到 `~/.local/share/htmlninefox`。
- 命令入口：`~/.local/bin/htmlninefox-app`。

## 安装

```bash
chmod +x install.sh
./install.sh
```

只安装不立即启动：

```bash
./install.sh --no-launch
```

## 启动 / 卸载

```bash
./run.sh
./uninstall.sh
```

## PDF / PNG 导出

系统需要 Chromium 或 Chrome。安装器会检测浏览器并给出提示；也可通过 `HTMLNINEFOX_BROWSER_PATH` 指定浏览器可执行文件。

## 构建发布包

```bash
python packaging/linux/download_wheels.py
python packaging/linux/build_linux.py
```

跨架构 wheelhouse 由构建脚本和发布 CI 生成，不提交到 Git 源码。
