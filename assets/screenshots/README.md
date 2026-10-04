# Screenshots · 产品截图与验收证据

截图按版本目录保存。历史目录记录当时发布状态；`v0.5.0rc3-visual/` 记录 2026-09-24 发布的 `v0.5.0rc3` 视觉基础切片。

## 目录清单

| 目录 | 用途 |
|---|---|
| `v0.3.0b2/` | 早期工作台、图库、引导创作和多类输出 |
| `v0.4.0/` ～ `v0.4.2/` | Pixel Garden、LLM、Docker、Export Center 与发布工作台 |
| `v0.5.0a1/` ～ `v0.5.0rc2/` | 交互、Recipe Run、Project Memory、Revision 与 RC2 发布证据 |
| 0.5.0rc3/ | Chromium 发布验收生成的纸白、夜蓝与 Export Center 截图 |
| `v0.5.0rc3-visual/` | `v0.5.0rc3` 的响应式、组件状态与恢复/错误证据 |
| `v0.6.0/` | `v0.6.0` 的工作台、设计吸收、PPTX 导出与历史功能实拍（23 张） |

## v0.6.2 截图（23 张 · 顶栏徽标均为 v0.6.2）

v0.6.2 是纯安全补丁，界面与 v0.6.1 逐像素相同，**但整目录仍重新实拍**——
沿用 v0.6.1 的图会让 Release 附上写着旧版本号的截图。`scripts/capture_core_shots.py`
的 tag、端口与输出目录现全部从包 `__version__` 推导，不再写死。

```bash
HTMLNINEFOX_V060_EVIDENCE_DIR=assets/screenshots/v0.6.2 python -m pytest \
  tests/test_v060_visual_evidence_states.py tests/test_v061_visual_evidence_states.py -q
FOX_DEMO_BASE=http://127.0.0.1:<port> python scripts/capture_core_shots.py
```

## v0.6.1 截图（23 张 · 顶栏徽标均为 v0.6.1）

v0.6.1 是补丁版本，界面与 v0.6.0 逐像素相同（代码差异只有 `lifecycle-slides.js` 的竞态守卫与两个新增测试），但**整目录重新实拍**——不是从 v0.6.0 复制。v0.6.1 的 5 张工作台主视图曾一度直接复用 v0.6.0 的图，实拍后发现顶栏徽标写的是 `v0.6.0`，那是关于附件内容的假声明，已改为由 `scripts/capture_core_shots.py` 重新采集并**逐张断言徽标**：

```bash
# 前 18 张：两个门禁产出（未设环境变量时只断言、不落盘）
HTMLNINEFOX_V060_EVIDENCE_DIR=assets/screenshots/v0.6.1 python -m pytest \
  tests/test_v060_visual_evidence_states.py tests/test_v061_visual_evidence_states.py -q
# 后 5 张：工作台主视图（需先起服务，脚本内断言 #ver == v0.6.1）
python -m htmlninefox.cli serve --host 127.0.0.1 --port 8636 --output .tmp/v061-core
python scripts/capture_core_shots.py
```

| 分组 | 文件 |
|---|---|
| 工作台与画布 | `workbench-overview` `workbench-paper-1440` `workbench-night-1440` `workbench-tablet-768` `workbench-mobile-390` `sidebar-templates` `mobile-library` |
| 输入与检查器 | `input-brief` `node-inspector` `output-inspector` `command-palette` |
| 状态与能力 | `project-memory` `revision-restore` `generation-cancel` `export-ready` `classic` |
| v0.6.0 主线功能 | `intake-review-pending` `intake-approved-absorption` `intake-preview-sandbox` `motion-lab-intake-motion` `slide-editor-dialog` `export-center-pptx` `pptx-export-report` |

## v0.6.0 截图（23 张 · 顶栏徽标均为 v0.6.0）

分两批采集，都由可复跑的门禁产出，**不是手工截图**：

**第一批 · v0.6.0 新功能**（`tests/test_v060_visual_evidence_states.py`）
`intake-review-pending` / `intake-approved-absorption` / `intake-preview-sandbox` /
`motion-lab-intake-motion` / `slide-editor-dialog` / `export-center-pptx` / `pptx-export-report`

**第二批 · 补齐「功能仍在但无 v0.6.0 实拍」的 19 项缺口**（`tests/test_v061_visual_evidence_states.py`）

| 分组 | 文件 |
|---|---|
| 工作台与画布 | `workbench-overview` `workbench-paper-1440` `workbench-night-1440` `workbench-tablet-768` `workbench-mobile-390` `sidebar-templates` `mobile-library` |
| 输入与检查器 | `input-brief` `node-inspector` `output-inspector` `command-palette` |
| 状态与能力 | `project-memory` `revision-restore` `generation-cancel` `export-ready` `classic` |

重采命令（两个门禁都受 `HTMLNINEFOX_V060_EVIDENCE_DIR` 控制；**未设置时只跑断言、不落盘**，
因此在 CI 上必跑且零副作用）：

```bash
HTMLNINEFOX_V060_EVIDENCE_DIR=assets/screenshots/v0.6.0 \
  python -m pytest tests/test_v060_visual_evidence_states.py tests/test_v061_visual_evidence_states.py -q
```

> **不要用 `e2e_verify.py` / `canvas_e2e.py` 补图**：两者都把输出目录写死为
> `assets/screenshots/v{__version__}/` 并直接 `mkdir` 写图，运行即污染版本化发布资产。

> `v0.5.0/` 下的 6 张仍是 `v0.5.0` 版式，README「六类真实产物」表继续引用它们并已注明版本。

## v0.5.0 稳定版截图（24 张）

发布于 `v0.5.0`（2026-09-25）后的完整实拍集，顶栏版本徽标为 `v0.5.0`：

- 布局与主题：`workbench-paper-1440.png`、`workbench-night-1440.png`、`workbench-night.png`、`workbench-overview.png`、`workbench-tablet-768.png`、`workbench-mobile-390.png`、`workbench-mobile-library.png`、`classic-pixel-garden.png`
- 对话框与检查器：`input-dialog-paper.png`、`selected-node-inspector.png`、`generated-output-inspector.png`、`export-center-ready.png`、`export-center.png`
- 业务状态：`command-palette-search.png`、`project-memory-saved.png`、`export-analysis-error.png`、`revision-restore-complete.png`、`generation-cancel.png`

`export-center.png` 由 `e2e_verify.py` 采集，展示真实导出产物（page-01.png + export-report.json）。

**真实产物输出（6 张，e2e 验收流程生成）**：`output-landing.png`、`output-dashboard.png`、`output-deck.png`、`output-deck-page2.png`、`output-poster.png`、`output-archdoc.png`。中英文 README 的功能 ↔ 截图对照画廊与「六类真实产物」表均引用本目录。

## RC3 视觉证据（15 张）

### 布局、主题与响应式

- `workbench-paper-1440.png`
- `workbench-night-1440.png`
- `workbench-tablet-768.png`
- `workbench-mobile-390.png`
- `workbench-mobile-library.png`
- `classic-pixel-garden.png`

### 组件与业务状态

- `input-dialog-paper.png`
- `command-palette-search.png`
- `selected-node-inspector.png`
- `generated-output-inspector.png`
- `project-memory-saved.png`
- `export-center-ready.png`
- `export-analysis-error.png`
- `revision-restore-complete.png`
- `generation-cancel.png`

这些截图覆盖默认、选中、搜索、保存成功、生成完成、导出就绪、受控错误、恢复完成和取消等待等可观察状态。完整说明见 [RC3 视觉收敛记录](../../docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)。

## v0.6.0 新功能截图（7 张）

只拍 `v0.5.0` 之后新增的功能，`v0.5.0` 系列已有的工作台、图库与导出画面不重复采集：

- `intake-review-pending.png`：素材审核台「待审核」列表——许可三档徽标、来源徽标、设计令牌色板、骨架大纲、批量工具条，以及顶部的吸收指标面板（候选 / 待审 / 已采纳 / 组件 / 动效 / 风格预设 / 来源分布）。
- `intake-preview-sandbox.png`：审核台 CSP 沙箱预览展开态——`sandbox` 不含 `allow-scripts`，服务端 `default-src 'none'` 兜底，候选脚本永不执行。
- `intake-approved-absorption.png`：审核台「已采纳」态——已采纳候选显示「生成风格预设 / 导入组件 / 吸收动效」按钮（按 kind 出现），三个动作各自入库后指标面板变为「组件 3 · 动效 1 · 风格预设 1」。
- `motion-lab-intake-motion.png`：动效实验室 `motion-lab` 的 07 号卡片——从已采纳参考生成的原创动效，时长被动效预算钳制（900ms → 500ms，300ms 保持），并随「减少动态效果」偏好降级。
- `slide-editor-dialog.png`：工作台内结构化幻灯片编辑对话框（S13U-b）——按页列出全部可编辑文本节点，状态行给出「共 7 页 · 修订基于 rev0」，保存即生成新版本。
- `export-center-pptx.png`：导出中心选择 PPTX 后的导出完成态——兼容性 100 分、引擎 `python-pptx`，结果区给出 `export-report.json` 与 `.pptx` 两个下载项。
- `pptx-export-report.png`：服务端返回的 `export-report.json` 正文——`pptx.editable_elements` 可编辑元素数、`pptx.slides` 页数与 `pptx_flattened` 降级清单。

> PPTX 格式项由 `static/index.html` 的 `#export-format-pptx` 登记，`renderAnalysis` 只在 deck 产物放开；采集脚本不再向页面注入任何临时 option，`export-center-pptx.png` 拍的是用户真实可选的路径。

## 命名与拍摄要求

- 工作台截图采用 `功能-主题-宽度.png` 或 `业务状态.png`。
- 标准验收 viewport 为 `1440×900`、`768×1024` 和 `390×844`。
- 同一组截图使用同一浏览器缩放、字体环境和测试数据。
- 截图必须呈现真实页面，且敏感信息、API Key、用户私密正文已移除。
- 错误截图使用可控失败注入，避免依赖网络偶发故障。
- 更新现有主视觉时，同时更新中英文 README、迭代记录和本清单。

## 可复现采集

`tests/test_rc3_visual_evidence_states.py` 通过真实工作台路径生成命令搜索、Project Memory 保存、Export 分析错误和 Revision Restore 完成状态。`tests/test_rc3e_lifecycle_modules.py` 追加生成取消等待状态（`generation-cancel.png`）。默认测试使用临时目录；需要重新生成仓库证据时，可将 `HTMLNINEFOX_RC3_EVIDENCE_DIR` 指向：

```text
assets/screenshots/v0.5.0rc3-visual
```

`tests/test_v060_visual_evidence_states.py` 同款方式产出 `v0.6.0/` 的 7 张新功能截图：审核台、动效实验室、幻灯片编辑对话框与 PPTX 导出报告。默认测试只跑断言不落盘；需要重新生成时将 `HTMLNINEFOX_V060_EVIDENCE_DIR` 指向：

```text
assets/screenshots/v0.6.0
```

提交前至少运行相关浏览器测试、JavaScript 语法检查和 `git diff --check`，并确认所有 Markdown 图片路径存在。
