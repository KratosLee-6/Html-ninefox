# Html九尾狐 · 安装包之外的顺畅运行方式

> 版本：v0.3.0 Beta 2
> 更新日期：2026-09-01

## 1. 方式对比

| 方式 | 需要 Python | 需要安装 | 适合场景 |
|---|---:|---:|---|
| Windows 便携 ZIP | 否 | 否 | Windows 日常使用、U 盘携带、客户演示 |
| Windows Setup EXE | 否 | 是 | 创建开始菜单和桌面快捷方式 |
| Linux 自解压 `.run` | 是，3.10+ | 用户级 | Ubuntu / Debian / Fedora 等桌面 Linux |
| Linux `.tar.gz` | 是，3.10+ | 可选 | 服务器、审计后手动部署 |
| `uv run` | 由 uv 管理 | 无需手动建环境 | 开发者、源码目录直接运行 |
| Docker Compose | 否 | 只需 Docker | NAS、服务器、团队共享 |
| 浏览器 PWA | 后端仍需运行 | 浏览器安装 | 像桌面应用一样打开工作台 |
| 局域网 / 远程浏览器 | 服务器需要 Python 或 Docker | 客户端无需安装 | 多台电脑、手机、iPad 共用 |

## 2. Windows 免安装便携版

解压 `HtmlNineFox-Windows-x64-0.3.0b2.zip`，双击 `HtmlNineFox.exe`。

- 内置 Python 运行时和依赖。
- 自动打开浏览器；8620 被占用时自动尝试后续端口。
- 数据与产物默认保存在包内 `user-data/`，移动整个目录即可迁移。
- 关闭控制台窗口即停止本地服务。

## 3. uv：源码目录零手动环境配置

Windows 双击 `run-with-uv.cmd`，Linux/macOS 执行：

```bash
chmod +x run-with-uv.sh
./run-with-uv.sh
```

或直接运行：

```bash
uv run htmlninefox app
```

uv 会自动创建隔离环境并安装项目依赖，不需要手动执行 `venv`、激活环境或逐项安装。

## 4. Docker Compose

```bash
docker compose up --build
```

打开 `http://127.0.0.1:8620`。停止：

```bash
docker compose down
```

数据保存在 Docker named volumes 中。

## 5. 局域网共享

在一台电脑或 NAS 上运行：

```bash
htmlninefox serve --host 0.0.0.0 --port 8620
```

同一局域网中的 Windows、Linux、macOS、iPhone、iPad 和 Android 设备可通过服务器 IP 访问。当前版本尚未提供登录鉴权，**不要把 8620 端口直接暴露到公网**；公网部署应放在带 HTTPS 和认证的反向代理后。

## 6. PWA

服务运行后，在 Edge 或 Chrome 中点击顶部“安装”。PWA 提供独立窗口、桌面图标和离线工作区壳，但生成与反馈仍依赖本地服务或远程服务。
