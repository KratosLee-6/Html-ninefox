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
| 标签构建与 GitHub Release 回读 | 标签推送后记录 |


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

## 尚未覆盖

- macOS / iOS Safari 与 Windows WebView2 实机。
- 多进程同时写入同一 Project 与突然断电后的跨文件事务恢复。
- Windows Authenticode 代码签名与 SmartScreen 信誉。
- 使用付费真实模型的 DSH 技能自主选择会话。
