# v0.7.6 发布说明 · 打包矩阵补齐：macOS Intel + Linux .deb

**发布日期**：2026-10-12
**上一版**：v0.7.5（2026-10-12）
**性质**：打包发布升级。**应用本身零变化**——新增的是两个平台缺口的包体
与它们的真实验证。

---

## 一句话

**macOS 用户第一次有 Intel 包可下，Debian/Ubuntu 用户第一次有 .deb 可装；
且这两类新包与既有的 macOS arm64 包一样，都在 CI 里被真实启动验证过，
发布前还要过字节级回读。**

---

## 打包矩阵（本版起）

| 平台 | 包体 | 真实启动验证 | 字节级回读 |
|---|---|---|---|
| Windows | `HtmlNineFox-Setup-<v>.exe` + `HtmlNineFox-Windows-x64-<v>.zip` | ✅ `verify_portable.py`（既有） | ✅ |
| macOS (Apple Silicon) | `HtmlNineFox-macOS-arm64-<v>.zip` | ✅ **本版起**：原生启动 + 健康/内容检查 | ✅ |
| macOS (Intel) | `HtmlNineFox-macOS-x64-<v>.zip` | ✅ 本版新增，Intel runner 原生构建+启动 | ✅ |
| Linux | `HtmlNineFox-Linux-amd64-<v>.deb` | ✅ 本版新增：apt 真装 + 启动烟囱 + 干净卸载 | ✅ 本版新增 |
| Linux | `HtmlNineFox-Linux-<v>.tar.gz` / `.run` | 启动脚本随包 | ✅ |
| Docker | 镜像（导出运行时就地断言） | ✅（既有） | — |
| Python | `htmlninefox-<v>-py3-none-any.whl` | 由测试套件覆盖 | ✅ |

全部附件附 SHA-256（`*.sha256.txt`）。

---

## Added

- **macOS Intel 便携包**：新 `macos-intel` job。PyInstaller 不能交叉编译，
  Intel 包在现役 Intel runner（macos-15-intel；上一代 macos-13 已退役）上
  原生构建、原生启动验证。
- **Linux .deb**：`HtmlNineFox-Linux-amd64-<版本>.deb`。装 `/opt/htmlninefox`
  （离线 wheelhouse，安装不需联网），postinst 构建 venv，postrm 带升级守卫
  （升级复用 venv、卸载清理）；入口 `/usr/bin/htmlninefox-app`（应用）与
  `/usr/bin/htmlninefox`（CLI），桌面入口进包。依赖
  `python3 (>= 3.10)`、`python3-venv`。
- **`packaging/verify_unix_portable.py`**：unix 版真实启动验证器，与
  Windows 的 verify_portable 同一纪律——health 报版本与发行形态、首页
  品牌标记、静态资源非空、**内容标记**（含 v0.7.5 引入的
  `window.FoxState`，陈旧产物在此被抓住）、干净退出。

## Changed

- macOS arm64/x64 两个 job 都把构建出的 .zip 解压、真实启动、过健康与
  内容检查——此前 macOS 只有构建 job 变绿，从不被执行。
- Linux .deb 在 ubuntu runner 上 `apt-get install` 真装（postinst 真建
  venv）、`htmlninefox --version`、启动烟囱、`apt-get remove` 干净卸载。
- `verify_release_assets.py` 学会读 .deb：自写 ar 解析器 + `data.tar.xz`
  内 wheel 前端回读（构建固定 `-Zxz` 保证标准库可读），`.deb` 进字节级
  回读清单。

---

## 门禁

| 门禁 | 拦什么 |
|---|---|
| `test_packaging_matrix.py`（6 条） | .deb 目录树逐项断言（postrm 升级守卫、Depends 的 python3-venv）；验证器正例（真实产物全链通过）；**验证器负例**（缺内容标记的假产物必须被拒绝——对验证器自己的变异检验）；workflow 矩阵形状；.deb 字节回读分支实读；烟囱旗子与 CLI 入口一致性 |
| 变异 `mutate_packaging_gates.py` | .deb 退出回读清单 / Depends 丢 python3-venv / 内容断言放水 / 旗子退回 --no-browser——**4/4 CAUGHT** |

## 真启动验证的第一次战果（发生在本版开发中）

v0.7.6 首次 CI 构建：.deb 正确安装（postinst 完成、`htmlninefox --version`
通过），但烟囱里 `htmlninefox app` 立即退出——它是 click 入口，旗子叫
`--no-open-browser`，而烟囱传了 desktop 入口的 `--no-browser`。**全套单元
测试全绿，只有真启动暴露**。这正是这道验证存在的理由；旗子已修正，并把
「workflow 传的旗子必须被 CLI 入口接受」锁进本机可跑的门禁。

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **657 passed / 4 skipped**（含本轮新增 5 条打包门禁：正例在真服务器上跑通，负例抓住缺标记产物） |
| 变异验证 | `mutate_packaging_gates.py` 3/3 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.7.6 一致 |

---

## 升级提示

- 应用与项目数据格式与 v0.7.5 完全一致，从 v0.7.0+ 任意版本可直接升级。
- Linux 用户若想换用 .deb：先跑用户级安装的 `uninstall.sh` 再装 .deb，
  避免两套入口并存。
- macOS Intel 包未做 Apple 公证，首次打开仍需右键 → 打开（同 arm64 包）。
