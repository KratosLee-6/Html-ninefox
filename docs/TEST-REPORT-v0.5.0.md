# v0.5.0 正式版测试报告

- 日期：2026-09-25
- 验证版本：`0.5.0`（tag `v0.5.0`，含 RC3-D `58c2c5d`、RC3-E `0381f46`）
- 关联 Issue：#6 · 总追踪 #2
- 结论：**全部可本地执行门禁在 0.5.0 最终版本号下通过**；Docker 与 Linux 附件由 tag 触发的发布工作流构建并验证；Safari 实机需要 macOS（已在 Release Notes 明示限制）。

## 门禁结果

| 门禁 | 结果 | 证据 |
|---|---|---|
| Python 全量（pytest） | **238 passed, 1 skipped** | 含 12 durability + 4 lifecycle 测试 |
| Chromium e2e（CI 同款） | **22 / 22 通过** | `e2e_verify.py`（bundled Chromium） |
| **WebView2 / Edge 实机** | **22 / 22 通过** | `HTMLNINEFOX_E2E_CHANNEL=msedge python e2e_verify.py`，真实 Windows 10 主机 + 系统 Edge 引擎，覆盖生成、反馈、画布、主题切换、导出中心真实分页分析、真实 PNG 导出、JS 零错误 |
| JavaScript 语法 | 11 个独立脚本 + 内联块全部通过 | `node --check` + `check_inline_js.py` |
| DeepSeek Harness | **2 / 2 通过** | `npm test`（integrations/deepseek-harness） |
| 版本一致性 | `release metadata consistent: v0.5.0`（`--tag v0.5.0`） | `check_release_version.py` |
| wheel 构建 | `htmlninefox-0.5.0-py3-none-any.whl`；资源审计确认 4 个 `lifecycle-*.js`、`sw.js`、`index.html` 已入包，并在干净 venv 安装烟测通过（CLI `--version` = 0.5.0） | `pip wheel` + venv 烟测 |
| Windows 便携包 | `HtmlNineFox-Windows-x64-0.5.0.zip`（发布附件）；SHA-256 回读校验一致 | 标签 CI 构建 + 下载回读 |
| Windows 便携包真机烟测 | 打包 exe 启动 → `/api/health` 报 `windows-portable` → 真实生成（verify ok）→ 真实 PNG 导出（`full-page.png`）→ 版本历史可读 | 本机实跑 |
| Docker | 本机 Docker Desktop 未运行；按发布流程由 tag 触发的 CI 专 job 构建并验证（`build-release-packages.yml`） | CI |
| Linux 安装包 / 归档 | 由 tag 触发的 CI 构建（x86_64 + aarch64 wheelhouse） | CI |
| Safari 实机 | **待补**：需要 macOS / Safari 环境（计划内外部条件） | — |
| 附件回读 | 套件内覆盖：附件-only 异步任务全链路（`test_async_job_accepts_attachment_without_prompt`）；上传→生成→产物消费路径通过 | pytest |

## 发布执行记录

1. ✅ `pyproject.toml` / `__init__.py` / `uv.lock` / 双 README / CHANGELOG / ROADMAP 版本号统一为 `0.5.0`，`check_release_version.py --tag v0.5.0` 通过。
2. `RELEASE-NOTES-v0.5.0.md` 与 `TEST-REPORT-v0.5.0.md` 从本报告与 Release Notes rc3 顺势收口。
3. 打 tag `v0.5.0` → CI 构建 Windows/Linux 全套附件 + Docker 验证 → GitHub Release 挂附件与 SHA-256。
4. Release 附真实工作台、错误、恢复、导出截图（`assets/screenshots/v0.5.0rc3-visual/` 15 张已就绪，含 `generation-cancel.png`）。
5. Safari 实机验证（若有 macOS 环境）补录后发布，或在 Release Notes 明示限制。
6. 发布后监控 CI、附件、Issue 与下载反馈。

## 复现命令

```bash
python -m pytest tests/ -q
python e2e_verify.py                        # bundled Chromium
HTMLNINEFOX_E2E_CHANNEL=msedge python e2e_verify.py   # 系统 Edge / WebView2 引擎
(cd integrations/deepseek-harness && npm test)
python scripts/check_release_version.py
python -m pip wheel . --no-deps -w dist/
python packaging/windows/build_portable.py
```
