# V0.6-S17 既有门禁不退化 · 验证证据

- 执行日期：2026-09-29
- 目的：v0.6.0 发布前复跑全部既有门禁（100 节点画布 / 20 revisions / 双引擎 e2e / DSH / a11y / JS 语法 / 发布元数据），确认 v0.6 吸收流水线与 PPTX 链路没有让老能力退化。
- 执行环境：Windows / Python 3.11.15 / Node v24.15.0 / Playwright chromium + webkit + system Edge 可用
- 起点提交：`a5d7a93`（v0.6-S13U-b, native v1）
- 结论：**门禁通过，但发现并修复 2 个真实缺陷**（见「缺陷」一节）。修复后全绿。

## 一、门禁结果

| 门禁 | 命令 | 结果 |
|---|---|---|
| Python + 浏览器测试套件 | `python -m pytest tests -q -p no:cacheprovider` | ✅ **303 passed, 1 skipped**（173s） |
| JavaScript 语法 | `node --check` × 13 个 static JS + `python scripts/check_inline_js.py` | ✅ 13/13 通过；inline 2 块（index.html）+ 1 块（motion-lab.html）通过 |
| 发布元数据一致性 | `python scripts/check_release_version.py` | ✅ `release metadata consistent: v0.5.0` |
| DeepSeek Harness 插件集成 | `npm ci && npm test`（integrations/deepseek-harness） | ✅ **2/2**：真实 Harness registry 发现/加载/重载/卸载；发布 tarball 在无源码与无生产依赖下可用 |
| Chromium 验收 | `python e2e_verify.py` | ✅ **22/22** |
| WebKit / Safari 引擎验收（S18） | `HTMLNINEFOX_E2E_ENGINE=webkit python e2e_verify.py` | ✅ **22/22** |
| 100 节点 / 20 revisions / a11y | 包含在 pytest 套件内（`test_rc2_revision_dialog_accessibility_and_100_node_gate` 等） | ✅ |

Chromium 与 WebKit 两通道均为 22/22，无引擎差异清单需要列出。

## 二、本轮发现并修复的缺陷

### 缺陷 1（严重）：deck 被别名到 landing 模板，整条可编辑 PPTX 链路失效

- **现象**：安装可选 `templates` extra（jinja2）后，`test_pptx_export` 3 个用例失败，报 `RuntimeError: 该产物不是分页 deck（未找到 slide 结构）`；`e2e_verify.py` 在「deck 翻页交互」处 30s 超时崩溃（等不到 `#cur` 页码 HUD）。
- **根因**：`htmlninefox/experts/generate_expert.py` 的 `_INTENT_TEMPLATE_ALIAS` 把 `deck` 映射到 `templates/landing.html`（注释写作「deck 用 landing 模板兜底（保留原行为）」）。Jinja2 模板路径一旦命中，就会**先于**原生生成器返回，于是 deck 请求被渲染成 hero/features/pricing 落地页，产物里没有任何 `<section class="slide">`。
- **影响面**：这不是一个导出 bug，而是生成端的 intent 不忠实——PPTX 文件桥（`export_deck_pptx`）、幻灯片编辑 API（`PUT /slides`）、导出中心 pptx 格式全部失去输入，即 v0.6 成果 **G4「可编辑 PPTX」在此环境下必然失败**；且失败点在生成端、报错点在导出端，极难定位。它同时违反联盟 manifest `guizang-ppt` 声明的 `fallback: local:deck` 语义。
- **为何此前没被发现**：CI 只装 `pip install -e ".[dev]"`，**不含 `templates` extra**，因此 CI 环境走原生 `generators/deck.py`，一切正常；本地若装了 jinja2 才会踩到。属于典型的「可选依赖改变主路径」缺陷。
- **修复**：deck 不再进入 landing 模板，回落到原生 `generators/deck.py`，产出真正的分页结构。实测 7 页 / 24 个可编辑元素，与 `fallback: local:deck` 一致。新增回归测试锁定该不变量（见 `tests/test_pptx_export.py::test_deck_generation_stays_intent_faithful_with_or_without_jinja2`）。
- **干净 HEAD 复现证据**：在 `a5d7a93` 的独立 worktree 上运行 `e2e_verify.py`，首行即 `[✗] 生成 landing`，deck 翻页检查超时崩溃；同一命令在修复后 22/22 通过。

### 缺陷 2（轻）：e2e doctype 判断大小写敏感，templates 家族装上即假失败

- **现象**：`e2e_verify.py` 断言 `html.startswith("<!doctype html>")`。原生生成器（`generators/_shared.py`）输出小写 `<!doctype html>`，而 `templates/landing.html` 等模板家族输出大写 `<!DOCTYPE html>`。HTML doctype 按规范大小写不敏感，因此装/不装 jinja2 会走到不同渲染路径并产生相反的门禁结果。
- **修复**：断言改为 `html[:15].lower().startswith("<!doctype html>")`，与渲染路径解耦。

## 三、遗留观察（不阻断发布）

- `tests/test_integration.py::test_feedback_token_extraction` 在一次全量运行中失败、单独运行与后续全量运行均通过，疑似受全量运行时长/顺序影响的偶发项。目前无稳定复现路径，建议 v0.6.x 观察，若再现则定位 `FeedbackLib` 深合并路径的时间相关行为。
- `e2e_verify.py` 运行时会按 `__version__` 写入 `assets/screenshots/v<版本>/`，本轮执行曾覆盖 `v0.5.0` 下 3 张已跟踪的发布截图（已 `git checkout` 还原）。若该副作用非有意设计，建议在 S20 调整截图输出目录或改为显式参数，避免验收脚本污染版本化发布资产。

## 四、结论

- v0.6 的吸收流水线（S04–S12）与 PPTX 链路（S13/S14/S13U-a/S13U-b）**未让既有能力退化**，双引擎 22/22 一致。
- 缺陷 1 属发布阻断级：它使 G4 在安装了 `templates` extra 的环境下不可用，而该 extra 是官方可选依赖。修复后 G4 在有/无 jinja2 两种环境下均成立。
- 建议在 S19 文档六件套中补一条面向用户的说明：**deck 产物在有无 jinja2 环境下现在保持同一分页结构**，并把「可选依赖不得改变主渲染路径」列入 Definition of Done。
