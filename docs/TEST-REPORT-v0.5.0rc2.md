# v0.5.0rc2 发布测试报告

日期：2026-09-18。发布版本：`0.5.0rc2`。本报告把开发阶段证据、发布前本地复验与标签构建分开记录，避免把源码测试等同于安装包测试。

## 验证层级

| 层级 | 范围 | 状态 |
| --- | --- | --- |
| 已合并开发证据 | Python / HTTP / Chromium、版本历史、动效、100 节点、DSH 插件 | 见下方历史 CI 与专项报告 |
| 发布前本地复验 | 元数据、JavaScript、完整 pytest、Chromium E2E、插件、wheel 隔离安装与导出 | 本次发布提交前执行 |
| 标签构建 | Windows ZIP / EXE、Linux `.run` / `.tar.gz`、wheel、SHA-256、Docker Chromium | `v0.5.0rc2` 标签工作流执行 |
| 发布后回读 | Release 状态、附件清单、下载文件与 SHA-256 | 标签工作流完成后执行 |

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
