# v0.5.0rc3 发布测试报告

日期：2026-09-24。环境：Windows、Python 3.13、Node.js、Playwright Chromium。

## 发布候选结论

| 验收项 | 结果 |
|---|---|
| 发布元数据与 `v0.5.0rc3` 标签匹配 | **通过** |
| 完整 pytest | **201 passed, 1 skipped，115.59 秒** |
| Chromium 产品端到端 | **22 / 22 通过** |
| JavaScript 与内联脚本 | **通过：7 个独立脚本和 3 个内联脚本块** |
| DeepSeek Harness 插件 | **2 / 2 通过** |
| Python wheel 隔离安装与资源审计 | **通过**；版本 `0.5.0rc3`，RC3 CSS / JS / Logo / manifest 完整 |
| 标签构建与 GitHub Release 回读 | **通过**；Windows、Linux、Docker 与 publish-release 全绿 |


- 本地候选 wheel：`htmlninefox-0.5.0rc3-py3-none-any.whl`
- SHA-256：`da4729a1a6ac5b4faec4b5a86f4b5e1313d780f8b4ef2b82330cbb0f4e66b139`
正式 Release 由标签工作流重新构建，应以 Release 附件及其 sidecar 为准。

RC3 候选包含 14 张真实状态截图。安装包资源审计必须确认 `pixel-garden-tokens.css`、`workbench-system.css`、`workbench-ui.js`、Logo、PWA manifest 和工作台 HTML 均来自隔离安装目录。

## 发布前命令

```powershell
python scripts/check_release_version.py
python scripts/check_release_version.py --tag v0.5.0rc3
python scripts/check_inline_js.py
node --check htmlninefox/server/static/canvas-engine.js
node --check htmlninefox/server/static/canvas-productivity.js
node --check htmlninefox/server/static/workbench-features.js
node --check htmlninefox/server/static/workbench-ui.js
node --check htmlninefox/server/static/motion-system.js
node --check htmlninefox/server/static/interaction-system.js
node --check htmlninefox/server/static/sw.js
python -m pytest -q --basetemp .codex_tmp/pytest-v050rc3 -p no:cacheprovider
python e2e_verify.py
npm test --prefix integrations/deepseek-harness
python -m pip wheel . --no-deps --wheel-dir .codex_tmp/wheel-v050rc3
```

## GitHub 发布结果

- [主分支 Test CI #35989145761](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35989145761)：版本一致性、DSH、完整 pytest、JavaScript 与 Chromium acceptance 全部通过。
- [标签构建 #35989459547](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35989459547)：Windows、Linux、Docker 与 publish-release 四个任务全部成功。
- [v0.5.0rc3 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc3)：非草稿、预发布；`v0.4.2` 继续保持稳定 Latest。
- Release 共 13 个附件：5 个应用包、5 个 SHA-256 sidecar、3 张 1440×900 Chromium 实测截图。
- 正式 wheel 已下载并在隔离目录安装，版本为 `0.5.0rc3`，`pixel-garden-tokens.css`、`workbench-system.css` 与 `workbench-ui.js` 均存在。

| 正式应用包 | GitHub SHA-256 digest |
|---|---|
| `htmlninefox-0.5.0rc3-py3-none-any.whl` | `91170ea22ead5c36fffb74f2cf3df74851fc47644f441d47a8b39a366e88787a` |
| `HtmlNineFox-Windows-x64-0.5.0rc3.zip` | `cff62dd3009bf5b8f217ec993de663c476c7b50be0a270015a6f8a8118a0da3d` |
| `HtmlNineFox-Setup-0.5.0rc3.exe` | `f2197698ebc56bcd408e30de206c1110843cf044e34ce8f7be74ed4e9f7771e2` |
| `HtmlNineFox-Linux-0.5.0rc3.run` | `b6ce8483a82e3b2f4ebc3fed7e78f69be5e07be048dddd0aee6ba4e3c7ee880c` |
| `HtmlNineFox-Linux-0.5.0rc3.tar.gz` | `e5520f46790a50df4b43aae1210ded75bb123973f1c774d7715934d11b2659b9` |

## 尚未覆盖

- macOS / iOS Safari 与 Windows WebView2 实机。
- 多进程同时写入同一 Project 与突然断电后的跨文件事务恢复。
- Windows Authenticode 代码签名与 SmartScreen 信誉。
- 使用付费真实模型的 DSH 技能自主选择会话。
