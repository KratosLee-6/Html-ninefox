# Html九尾狐 Linux 安装包

两种形态，任选其一：

| 形态 | 适合 | 位置 | 入口 |
|---|---|---|---|
| `.deb`（`HtmlNineFox-Linux-amd64-<版本>.deb`） | Debian/Ubuntu，想要升级与卸载语义 | `/opt/htmlninefox`，安装时构建 venv | `/usr/bin/htmlninefox-app`（应用）/ `/usr/bin/htmlninefox`（CLI） |
| `.tar.gz` / `.run`（用户级） | 其余发行版、无 root、绿色安装 | `~/.local/share/htmlninefox` | `~/.local/bin/htmlninefox-app` |

两种形态共用同一离线 wheelhouse（`wheels/`，含 x86_64 / aarch64 的 Playwright
驱动依赖），安装不需要联网。

## .deb 安装 / 卸载

```bash
sudo apt-get install ./HtmlNineFox-Linux-amd64-<版本>.deb   # 或 dpkg -i + apt -f install
htmlninefox-app            # 应用（http://127.0.0.1:8620）
htmlninefox --version      # CLI
sudo apt-get remove htmlninefox
```

依赖 `python3 (>= 3.10)` 与 `python3-venv`；升级时 venv 复用（postrm 有
upgrade 守卫），卸载时清掉 venv，用户数据始终保留。

## 用户级安装（tar.gz / .run）

- 不需要 sudo，不修改系统 Python。
- 支持 Linux x86_64 / aarch64 与 Python 3.10–3.13。
- 命令入口：`~/.local/bin/htmlninefox-app`。

```bash
chmod +x install.sh
./install.sh            # 只安装不启动：./install.sh --no-launch
./run.sh                # 启动
./uninstall.sh          # 卸载
```

## PDF / PNG 导出

系统需要 Chromium 或 Chrome。安装器会检测浏览器并给出提示；也可通过 `HTMLNINEFOX_BROWSER_PATH` 指定浏览器可执行文件。

## 构建发布包

```bash
python packaging/linux/download_wheels.py
python packaging/linux/build_linux.py   # tar.gz + .run
python packaging/linux/build_deb.py     # .deb（Linux 上执行；--stage-only 任意平台可测）
```

跨架构 wheelhouse 由构建脚本和发布 CI 生成，不提交到 Git 源码。
CI 在 ubuntu runner 上真实安装 .deb 并启动验证（`verify_unix_portable.py`），
发布前 `verify_release_assets.py` 会对 .deb 做字节级回读。
