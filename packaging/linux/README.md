# Html九尾狐 Linux 用户级安装包

- 不需要 sudo，不修改系统 Python。
- 支持 Python 3.10–3.13。
- 离线依赖位于 `wheels/`；安装到 `~/.local/share/htmlninefox`。
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
