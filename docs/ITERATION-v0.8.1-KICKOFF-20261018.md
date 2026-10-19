# v0.8.1 开工记录 · 2026-10-18

**版本主题**：DOCX 导入 ＋ AI 理解补全（`docs/PLAN-v0.8.md` 第 1 节）
**开工日**：2026-10-18（v0.8.0 发布次日）
**Day-1 原则**：先拆掉「每次发版必红」的地雷，再动新功能。红落在 tag 上，会让后面每一次验证都失去可信度。

---

## 1. 完成项

### 1.1 变异诊断层（CI 噪音的根因）

**问题**：v0.7.7 / v0.7.8 / v0.8.0 三个 release commit 的 CI 全红，随后补一条 `fix: realign ...` 才绿。根因不是产品坏了，而是变异脚本的**字面锚点**被源码改动打飞：

| 版本 | 变异 | 锚点死因 |
|---|---|---|
| v0.8.0 | M8 `SUPPORTED_FORMATS` | 格式元组从 `("pdf","png","pptx")` 扩到含 `docx` |
| v0.7.8 | U3 / U4 | `onclick=` 字面量 → C6 全量迁 `data-action` |
| v0.7.7 | P3 provenance | 二档 → 三档 |

**改法**：
- 新增 `scripts/mutation_support.py`：把红分成两类，给不同退出码——`1 MISSED`（门禁有洞，真漏洞）/ `3 STALE`（锚点过期，测试体系问题），并打印 `文件:行`＋期望片段＋最近邻行＋下一步。
- `scripts/mutate_smoke_gates.py`：M8、M4 改用**结构锚点**（正则），命中即用，不再依赖整行字面量；失败时输出完整 STALE 诊断块。
- `scripts/mutate_ui_gates.py` / `scripts/mutate_page_blocks_gates.py`：`HARD FAIL` 改为 `STALE`，接入统一退出码。
- 新增 `scripts/preflight_mutations.py`：一条命令跑完三套变异，**发版前本地预跑**，让红留在本地而不是落在 tag 上。

### 1.2 DOCX 解析器（v0.8.1 管线第 1 步 · 离线）

新增 `htmlninefox/docx_import.py`（标准库 `zipfile` + `ElementTree`，不依赖 `[docx]` extra）：

- 产出 `docx_outline` 交接产物：标题层级（Heading 1–6 / Title）、段落、列表（`numPr` → 深度）、表格（行列）、**内嵌图片提取**（`word/media/*` 成为资产候选）、文档标题（`docProps/core.xml` 的 `dc:title` 优先）；
- 双形态：`DocxOutline` 对象 ＋ `as_dict()` 机器可读形态（外部 agent 可驱动）；
- **降级如实**：未读取的部件逐个列进 `warnings`，不静默丢；
- 坏文件明确报错（`DocxIntakeError`），不半解析。

**真实文档验证**：`E:/工作/01_业务/【汐构科技】/GEO/汐构信息技术全域数字营销与GEO平台定制方案_含产品架构图.docx`

```
title   极简科技全域数字营销与 GEO 平台定制方案   ← 取自 dc:title，不是「目录」
counts  {heading: 54, paragraph: 34, table: 48, image: 1}
assets  word/media/geo_product_architecture.png
warnings 未读取的部件 7 个（header/footer/numbering/settings/styles…）
```

> 这一跑暴露了一个真实缺陷：第一个 Heading1 是「目录」，直接拿它当标题会让整份提案在审核台上显示成「目录」。已改为「core.xml 的 dc:title → 第一个非目录标题」，并补了门禁。

### 1.3 统一契约 `intake_outline`（KX 2026-10-18 定：统一收敛）

新增 `htmlninefox/intake_outline.py`，把「读进来的东西」定成一种形状，PPTX / PDF / HTML 之后共用：

- `SourceInfo`（kind / ref / digest / origin / licence / title）
- `AdapterInfo`（name / version / offline / requires）
- `Block`（kind / heading / content / level / rows / asset / provenance / **evidence** / ordinal）
- `IntakeOutline`（source / adapter / blocks / assets / **limitations**）＋ `validate()` ＋ `as_dict()`

**两条硬规则**（借自 REA）：
1. **每个 block 必须有可回指的 locator**（DOCX：1-based 段落序号；表格带 `table: true`；图片带 `part`）。`validate()` 直接拒绝没有定位的块——没有证据的结论不进审核台。
2. **limitations 是交付物**，不是日志：未读取的部件、缺标题、图片引用缺失都逐条列出。

`parse_docx` 现在返回 `IntakeOutline`（不再有 DOCX 专属模型），DOCX 只是第一个适配器。

### 1.4 提案层（v0.8.1 第 2 步，离线规则版）

新增 `htmlninefox/docx_proposal.py`：`propose(outline) -> Proposal`，产出审核台要看的四件东西：

| 字段 | 内容 | 例子（真实 GEO 方案） |
|---|---|---|
| `intent` ＋ `intent_reason` | 意图判定与理由 | `doc` ← 54 个标题 / 34 段正文 / 48 张表 |
| `style` ＋ `style_reason` | 落到既有预设，不新建风格 | `doc-clean` ← doc × professional |
| `image_plan` | slot ＋ 用途 ＋ 提示词（只给提示词，不直出图） | `cover`、`section-1..3` |
| `copy` | headline / summary / sections / key_points，可编辑 | 摘要压成单行，目录不进章节 |
| `limitations` | 继承 outline ＋ 本轮自己的边界 | 「未配置 LLM：规则引擎给出」 |

`refiner` 钩子留给 LLM：覆盖结果仍走 `validate()`，坏提案（未知意图/预设、缺提示词）直接抛错，不会半成品上桌。

### 1.5 门禁

- `tests/test_docx_import.py` **11 条**：标题/段落/列表/表格/图片资产/bytes 等价/坏 zip/缺 document.xml/降级清单/机器形态/**每块都有定位**/契约拒绝无定位块/目录标题不被误用/`dc:title` 优先。
- `tests/test_docx_proposal.py` **14 条**：五种意图判定（doc/deck/archdoc/poster/dashboard）、风格与理由、图片计划（cover 唯一、提示词非空）、文案（headline/summary/章节上限）、limitations 继承、机器形态、非法预设报错、refiner 覆盖与坏 refiner 报错、**目录不进章节/配图位**、摘要压成单行。

---

## 2. 验证

| 项 | 结果 |
|---|---|
| `pytest tests/test_docx_import.py` | **11 passed** |
| `pytest tests/test_docx_proposal.py` | **14 passed** |
| `pytest tests/test_docx_adopt.py` | **11 passed**（六意图 × 正文到达 ＋ 表格压平 ＋ 图片留资产 ＋ 真实文档 20k+ 字符） |
| 真实 .docx 解析 | 通过（54 标题 / 48 表格 / 1 图片 / `evidence_complete=True`） |
| 真实 .docx 提案 | `doc` ＋ `doc-clean`，封面＋3 个章节配图位，摘要单行，目录被排除 |
| `mutate_smoke_gates.py` | **9/9 CAUGHT**（M8 用新结构锚点后恢复 CAUGHT；此前是 `NOT APPLIED`） |
| `mutate_ui_gates.py` | **8/8 CAUGHT** |
| `mutate_page_blocks_gates.py` | **7/7 CAUGHT** |
| `preflight_mutations.py`（三套合一） | **通过，退出码 0**（2026-10-18 实跑） |
| 全量回归（本机） | 687 passed / 9 skipped / 2 failed —— 两条均已查明：socket flaky（重跑绿）＋ `.venv` 缺 `python-docx`（装上后 docx 导出 9/9 绿） |
| GitHub Actions · `Test` | **success**（run 39129995627，2026-10-18） |

---

## 3. 下一步（v0.8.1 管线第 2–5 步）

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 上传解析（离线）：`docx_outline` ＋ 统一 `intake_outline` 契约 | ✅ 完成（11 条门禁） |
| 2 | `docx_proposal`：意图 / 风格 / 图片计划 / 文案（离线规则 ＋ LLM refiner 钩子） | ✅ 完成第一版（14 条门禁） |
| 3 | 审核台呈现：上传 .docx、提案可改可拒、图片位增删、文案可编辑 | ⏭ 下一步（1.5 天，受 v0.8.2 界面规则约束） |
| 4 | 采纳生成：blocks → 既有分块通道（六生成器零改动） | ✅ 完成（11 条门禁，六个意图逐个断言正文到达；真实 GEO 文档 20k+ 字符） |
| 5 | 门禁：真链验收（真实 docx → 六类产物）＋ 无 LLM 兜底锁定 ＋ 提案 schema 锁定 ＋ 变异 | ⏭ 待 4（1 天） |

---

## 4. 未做与边界

- **图像模型直出**仍不在本版：图片计划只交付「提示词 ＋ 占位」；Provider 选型是独立决策点。
- **不做**新渲染路径：采纳后走既有 blocks 通道，六个生成器不改。
- `.docx` 的样式表（`word/styles.xml`）未解析：标题层级靠 `w:pStyle` 的命名约定，自定义样式名会退化成段落。这一条要在第 2 步的门禁里显式锁定（宁可退化为段落，也不猜）。
