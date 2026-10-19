# v0.8.1 发布说明 · Word 导入：解析 → 提案 → 采纳

**发布日期**：2026-10-19
**上一版**：v0.8.0（2026-10-17）
**性质**：新能力。HTTP 新增两个端点（`/api/intake/docx`、`/api/intake/docx/adopt`）；
项目数据格式不变，旧项目照常打开。规划：`docs/PLAN-v0.8.md`；
开工记录：`docs/ITERATION-v0.8.1-KICKOFF-20261018.md`。

---

## 一句话

**一份 `.docx` 进工作台，先看到「它被怎么理解」的提案——意图、风格、图片位、
标题与摘要都可改——人审完再一次点击成页。解析在本机完成，不联网也能用。**

---

## Added · Word 导入链路

- **离线解析**：纯 stdlib（`zipfile` + `ElementTree`）读 `word/document.xml`、
  `word/_rels`、`word/media`、`docProps/core.xml`；标题取 `dc:title` 优先，
  首个非「目录」标题兜底。真实方案实测：54 标题 / 48 表格 / 34 段落 / 1 图。
- **统一契约 `intake_outline`**：`Block` 携带 `provenance` 与 `evidence`
  （段落号 / 表号），`validate()` 直接拒绝没有 locator 的块——没有出处的内容
  进不来。
- **提案层 `docx_proposal`**：给出意图（含理由）、风格预设（含理由）、
  图片计划（slot + 用途 + 提示词）、文案（标题 / 摘要 / 章节 / 要点）与
  `limitations`。未配置模型时由规则引擎产出，`refined_by="rules"` 明确标注；
  留 `refiner` 钩子给外部模型，返回结果仍要过 `validate()`。
- **审核台**：上传 → 提案全可见并可改（意图 / 风格 / 标题 / 摘要 / 图片位增删）
  → 采纳生成。主按钮贴底常驻；390px 单列堆叠，实测 0 元素越界。
- **采纳生成**：提案转成既有分块通道的 `kind: sections` 块，走
  `StudioApplication.generate`，六个生成器零改动——不新建第二条渲染路径。
- **caller-owned 文案**：`GenerationRequest.content` 让审核台改过的标题与摘要
  在 `brief_expert` 之后覆盖规则文案；空字符串只对 `brand` 生效（显式空 = 不印
  品牌，不是"用占位符"）。

## Fixed · 三个只有实拍才发现的缺陷

1. **占位符漏进产物**：`brand_of()` 把显式空品牌兜底成 `Your Product`，
   客户的方案顶着占位符发出去。现在区分「缺字段（演示兜底）」与「显式空（不印）」。
2. **目录整段混进正文**：Word 的目录是「提示句 + 01/02 条目」的普通段落，
   800 字会拼成首节巨型段落。命中 `_TOC_HINTS` 后进入目录模式，连带跳过数字
   条目，直到遇见真标题，并在 `limitations` 里写明。
3. **面板整块空白**：新增的 `docx-desk.js` 未登记 `STATIC_FILES` 白名单 →
   404 → 脚本不执行。登记后恢复；这类失败不会报错，只会看起来"没做"。

## Gates

| 项 | 结果 |
|---|---|
| `tests/test_docx_import.py` | 11 passed |
| `tests/test_docx_proposal.py` | 14 passed |
| `tests/test_docx_adopt.py` | 13 passed（六意图 × 正文到达 / 表格压平 / 目录跳过 / 无占位符 / 真实文档 20k+ 字符） |
| `tests/test_docx_intake_api.py` | 14 passed（上传 / 错误码 / 采纳 / 改意图改风格 / 删图片位 / 六意图真链） |
| `tests/test_docx_proposal_schema.py` | 3 passed（键集合锁定 ＋ 离线兜底自述） |
| `tests/test_docx_desk_ui.py` | 1 passed（真浏览器：上传 → 改 → 采纳 → 产物含原文） |
| `scripts/mutate_docx_intake_gates.py` | **6/6 CAUGHT** |
| `scripts/preflight_mutations.py` | 五套变异全绿，退出码 0 |
| 全量回归（本机） | **741 passed / 4 skipped / 0 failed**（7 分 22 秒） |

## Known limits（随界面与接口一起交付）

- 表格压成文本行：列宽、合并单元格、边框不随行。
- 图片保留为资产，不内联进页面。
- `word/styles.xml` 未解析：自定义样式名会退化为段落（宁可退化，也不猜）。
- 未配置模型时，意图与风格来自规则引擎——界面上标签是 `rules`，不要当成模型判断。
- 图像模型直出不在本版：图片计划只交付「位 + 用途 + 提示词」。

## Upgrade notes

- 无数据迁移。旧项目、旧模板、旧导出全部照常。
- 新端点只读上传内容，不写入源 `.docx`；采纳产物落在常规输出目录，带版本历史。
- CLI 行为不变；Word 导入目前只在工作台（HTTP）提供。

## 文件

- 新增：`htmlninefox/intake_outline.py`、`htmlninefox/docx_proposal.py`、
  `htmlninefox/docx_adopt.py`、`htmlninefox/server/static/docx-desk.js`、
  `scripts/mutate_docx_intake_gates.py`、`scripts/capture_v081_desk*.py`
- 修改：`htmlninefox/docx_import.py`（返回统一契约）、`htmlninefox/application.py`
  （`content` 字段）、`htmlninefox/pipeline.py`（`_apply_caller_copy`）、
  `htmlninefox/generators/_shared.py`（`brand_of` / `brand_line`）、
  `htmlninefox/server/app.py`（两端点 + 静态白名单）、`README.md`、`README.en.md`
