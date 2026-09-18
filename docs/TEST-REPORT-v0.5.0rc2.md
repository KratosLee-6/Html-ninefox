# v0.5.0rc2 发布测试报告

日期：2026-09-18。发布版本：`0.5.0rc2`。本报告把开发阶段证据、发布前本地复验与标签构建分开记录，避免把源码测试等同于安装包测试。

## 验证层级

| 层级 | 范围 | 状态 |
| --- | --- | --- |
| 已合并开发证据 | Python / HTTP / Chromium、版本历史、动效、100 节点、DSH 插件 | 见下方历史 CI 与专项报告 |
| 发布前本地复验 | 元数据、JavaScript、完整 pytest、Chromium E2E、插件、wheel 隔离安装与导出 | 本次发布提交前执行 |
| 标签构建 | Windows ZIP / EXE、Linux `.run` / `.tar.gz`、wheel、SHA-256、Docker Chromium | **通过** |
| 发布后回读 | Release 状态、附件清单、正式 wheel 与 SHA-256 | **通过** |

## 发布前本地结果

| 验收项 | 结果 |
| --- | --- |
| 发布元数据与 `v0.5.0rc2` 标签匹配 | 通过 |
| 内联 JavaScript 与 6 个独立脚本 | 通过 |
| 完整 pytest | **198 passed, 1 skipped，88.73 秒** |
| Chromium 产品端到端 | **22 / 22 通过** |
| DSH 插件注册与最终 tarball 安装 | **2 / 2 通过** |
| Python wheel | 构建成功；隔离安装后版本、CLI 与 `motion-lab.html` 资源通过 |
| wheel 真实工作流 | 离线生成海报并导出完整 PNG，兼容性 **100 分** |
| Windows 便携包 | PyInstaller 构建成功；可执行文件启动后 `/api/health` 返回 `0.5.0rc2` / `windows-portable` |

本机因无创建符号链接权限，`test_external_revision_symlink_is_rejected` 跳过；此前 Linux CI 已运行并通过该项。其余测试无失败。

本地 Windows 候选 ZIP：`HtmlNineFox-Windows-x64-0.5.0rc2.zip`，SHA-256 为 `5F51ADAB40E4EFFE0A893B49ACEBB41269C5264FF92E37EAFDBD8F8948826348`。正式 Release 由 GitHub Actions 重建，必须使用 Release 同名 `.sha256.txt`，不能把本地候选值当作正式资产校验值。

## GitHub 发布结果

- [常规 Test CI #35358695358](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35358695358)：**199 passed，62.95 秒**；Chromium **22/22**；DSH **2/2**；JavaScript 与版本元数据通过。
- [标签构建 #35358991909](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35358991909)：Windows、Linux、Docker 与 publish-release 四个任务全部成功。
- [v0.5.0rc2 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc2)：非草稿、预发布；稳定 Latest 保持 `v0.4.2`。
- Release 共 13 个附件：5 个应用包、5 个 SHA-256 sidecar、3 张 `v0.5.0rc2` 实测截图。
- 正式 wheel 已完整下载，SHA-256 与 sidecar、GitHub asset digest 一致，并从隔离环境 `site-packages` 导入为 `0.5.0rc2`。
- 其余四个大包的 sidecar 内容均与 GitHub 对对应完整资产计算的 digest 一致。

| 正式应用包 | SHA-256 |
| --- | --- |
| `htmlninefox-0.5.0rc2-py3-none-any.whl` | `49a033de934365e7db9b4b0bc7a75e2d52e6536b4176557c77dfbd9fcf41091d` |
| `HtmlNineFox-Windows-x64-0.5.0rc2.zip` | `13a826e0b9b0ea4b0439ad4e8c51267681823e19d9883b092067ba1a5ac04d96` |
| `HtmlNineFox-Setup-0.5.0rc2.exe` | `ef68a79db42d83a3b5a3d585c31a4e35a911939647c104bc49a26a5a55dc29d0` |
| `HtmlNineFox-Linux-0.5.0rc2.run` | `2822b84d3ef4925d624e5f940c10c5121400bbc6f7c0c31c8d6f95c6e80ae190` |
| `HtmlNineFox-Linux-0.5.0rc2.tar.gz` | `4290e7dcd122e73deac1b472e4b433b6e71e820a878f3def74ae9b3e5a5a187d` |

## 已有可追溯证据

- [GitHub Actions #35353907293](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35353907293)：199 项 Python / 浏览器测试通过，Chromium 端到端 22/22，通过发布元数据与 JavaScript 检查。
- [RC2 功能报告](TEST-REPORT-RC2-20260918.md)：版本差异、恢复、冲突、失败保护、键盘、390px 与 100 节点门禁。
- [动效交付记录](ITERATION-MOTION-20260918.md)：三档动效偏好、竞态清理、资源打包与浏览器专项。
- [DSH 集成记录](DEEPSEEK-HARNESS-INTEGRATION.md)：插件 2/2、最终 tarball 独立安装、Release 回读与截图证据。

## 发布前复验命令

```powershell
python scripts/check_release_version.py
python scripts/check_release_version.py --tag v0.5.0rc2
python scripts/check_inline_js.py
node --check htmlninefox/server/static/motion-system.js
node --check htmlninefox/server/static/interaction-system.js
node --check htmlninefox/server/static/canvas-engine.js
node --check htmlninefox/server/static/canvas-productivity.js
node --check htmlninefox/server/static/workbench-features.js
node --check htmlninefox/server/static/sw.js
python -m pytest tests -q --basetemp .codex_tmp/pytest-v050rc2 -p no:cacheprovider
python e2e_verify.py
npm test --prefix integrations/deepseek-harness
python -m pip wheel . --no-deps --wheel-dir .codex_tmp/wheel-v050rc2
```

wheel 冒烟从隔离目录安装后执行版本、CLI、静态资源、离线生成和真实 PNG 导出，确保没有从源码目录误导入。Windows 与 Linux 最终包由标签工作流在对应操作系统构建；Docker 只验证本次源码构建的镜像，不声称已发布公共镜像。

## 尚未覆盖

- macOS / iOS Safari 与 Windows WebView2 实机。
- 多进程同时写入同一项目、突然断电后的跨文件事务恢复。
- 100 个动态 iframe 的长期帧率与内存。
- 使用付费真实模型的 DSH 技能自主选择会话。
- Windows Authenticode 代码签名与 SmartScreen 信誉。
