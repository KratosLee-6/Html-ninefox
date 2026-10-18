# 反向拆解：从 REA 借什么，以及要不要吃 PPT / PDF / Word / 图片

**日期**：2026-10-18
**起因**：KX 提到 [morluto/rea](https://github.com/morluto/rea)（Reverse Engineer Anything，MCP），问有没有可用的经验；并问反向拆解是否需要覆盖 PPT / PDF / Word / 图片。
**结论先说**：
1. **REA 值得借的不是它的逆向工具链，而是它的「结论必须带证据与边界」这套契约**——我们现在的 `page_blocks_from_candidate` 只有 provenance（版权）没有 evidence（指回源位置），也没有 limitations（拿不到什么）。
2. **需要覆盖 PPT / PDF / Word / 图片，但不能当成一件事做。** 四种格式「能拿到什么」差别巨大，必须一个格式一个适配器，各自如实标注边界。建议顺序：**PPTX（零新依赖）→ PDF（一个纯 Python extra）→ 图片（只做增强 provider，不默认开）**。Word 已经在 v0.8.1 落地。

---

## 1. REA 的做法，值得借的 5 条

| # | REA 的做法 | 我们现在 | 应落到哪里 |
|---|---|---|---|
| 1 | **每条结论带 evidence，并写明 limitations**（"results include the evidence and limitations behind each conclusion"） | blocks 只有 `provenance`（版权三档），没有「这条来自哪」与「哪些没拿到」 | `blocks[].evidence` ＋ 顶层 `limitations[]`，UI 在审核台逐条显示 |
| 2 | **按 target 分适配器，并列出前置条件表**（native 要 Hopper/Ghidra/IDA，JS 只要 Node，APK 要 JADX…） | HTML 一条路，其它格式没有入口 | `intake_adapters` 注册表，每个声明 `requires` / `offline` / `limits` |
| 3 | **provider 是外部能力，REA 不安装也不更新它们** | 我们已有先例：`[docx]` extra 未装时给 pip 提示，不自动装 | 沿用这条纪律：PDF/OCR 依赖也只提示，不偷偷装 |
| 4 | **本地分析，结论可导出、可快照** | 本地优先已有；版本快照已有（revisions） | 把 `intake_outline` 也纳入 revision 快照，便于回溯「当时是怎么拆的」 |
| 5 | **同一套能力同时给 agent 与终端**（MCP ＋ CLI 同构） | 有 HTTP API ＋ `skill/`；没有 MCP 工具 | 一个 MCP 工具 `intake_decompose`，**内部复用现有 HTTP API**，不另起服务 |

### 不该照搬的
- **二进制/汇编那条线**（Hopper / Ghidra / IDA / Frida / adb / 固件）：与产品无关，装上也用不到，且都是重型外部依赖。
- **运行时行为捕获**（进程、抓包、pcap）：我们的场景是「看一个页面/文档长什么样」，不是「审一个程序干了什么」。
- **多语言 README 铺开**：REA 有 20 种语言，是因为它面向全球逆向社区；我们先把中文＋英文两版维护好。
- 但有一条**供应链纪律**值得抄：REA 在 README 明写「相似的仓库名或复制的 README 不代表官方下载源」。我们已经有 NOTICE，可以在 README 补一句「唯一官方仓库」。

---

## 2. 我们现在的反向拆解长什么样

```
URL / ZIP ──► intake.fetch（SSRF 防护）──► candidate（许可三档）──► 审核台
                                                                    │
                                          page_blocks_from_candidate └─► blocks[] ──► 生成器
```

`page_blocks_from_candidate` 产出的每条 block：

```json
{"id":"page-section-1","kind":"sections","heading":"…","content":"…",
 "provenance":"verbatim|paraphrased|structure_only",
 "source_tag":"section","source_class":"hero","source_url":"…","ordinal":0}
```

**缺两样东西**：
1. **evidence**——只有 `source_tag` / `source_class`，没有可核对的位置（CSS 路径、字符区间、页码、slide 号）。人审时无法回答「这条是从哪儿拆出来的」。
2. **limitations**——拿不到的东西（JS 渲染后的内容、图片里的文字、扫描页）没有出现在结果里，等于默认「全拿到了」。

---

## 3. 统一契约：`intake_outline`（跨格式）

不给每种格式各造一套 blocks——**一套契约，多个适配器**。v0.8.1 的 `DocxOutline` 应收敛到这里。

```json
{
  "source": {"kind": "html|docx|pptx|pdf|image",
             "ref": "本地路径或 URL", "digest": "sha256:…",
             "origin": "user_upload|public_url", "licence": "open|reference|inspiration-only|user_owned"},
  "adapter": {"name": "docx", "version": 1, "offline": true, "requires": []},
  "blocks": [{
      "id": "b1", "kind": "heading|paragraph|list|table|image|section",
      "heading": "…", "content": "…", "level": 2, "rows": [],
      "provenance": "verbatim|paraphrased|structure_only",
      "evidence": {"path": "body > section.hero > h1", "page": null,
                   "slide": null, "paragraph": 12, "chars": [0, 42]},
      "source_url": "…", "ordinal": 0
  }],
  "assets": [{"part": "word/media/image1.png", "bytes": 12345, "alt": "…"}],
  "limitations": ["第 3–5 页是扫描图，未提取文本", "JS 渲染内容未执行，仅静态 DOM"]
}
```

三条硬规则：
1. **每个 block 必须有 `evidence`**，至少一个可回指的位置（HTML: CSS 路径；DOCX: 段落序号；PPTX: slide 号＋形状序号；PDF: 页码＋字符区间）。没有 locator 的 block 不允许进审核台。
2. **`limitations` 是交付物的一部分**，不是日志。UI 必须显示，导出报告必须携带。
3. **`origin=user_upload` 的许可按「用户自己的文件」处理**：默认 verbatim 可用、不外传；这与公开网页的三档许可不是同一套规则，不能混用。

---

## 4. 四种格式：能力边界与成本（回答 KX 第二问）

| 格式 | 能拿到 | 拿不到（必须写进 limitations） | 实现 | 新依赖 | 优先级 |
|---|---|---|---|---|---|
| **DOCX** | 标题层级、段落、列表、表格、内嵌图片、core 标题 | 自定义样式名的标题会退化成段落；页眉页脚/批注不读；不改版式 | `docx_import.py`（stdlib zip＋XML） | **无** | ✅ v0.8.1 已完成 |
| **PPTX** | 每页标题与要点文本框、表格、图片、讲稿备注、页序 | **布局几何不还原**（坐标/母版/主题效果）；图表与 SmartArt 只计数；合并单元格会丢结构 | `python-pptx` 只读遍历 `slides → shapes → text_frame` | **无**（导出已在用） | ⭐ 下一优先 |
| **PDF** | 文本层、页码、字块坐标（可用于判断栏位/标题层级） | **扫描件无文本层＝拿不到任何文字**；表格靠坐标猜，版面还原不可能；公式/图注常碎 | `pdfminer.six`（纯 Python）；无文本层时如实报"无文本层" | 一个 `[pdf]` extra | 次优先 |
| **图片** | 尺寸、主色/色板、可做占位与封面 | **文字内容拿不到**（除非 OCR/视觉模型）；版式只能靠视觉模型描述，误差不可控 | `PIL` 取尺寸/主色；文字转写走**可选 provider**（本地 OCR 或视觉模型） | OCR/视觉 provider（外部） | 最后，且默认关 |

### 为什么 PPTX 排在 PDF 前面
1. **零新依赖**：`python-pptx` 已经是导出侧依赖，读是同一套对象模型的反向遍历。
2. **场景命中率最高**：deck 是我们的主力产物；用户手里最多的「拿来改」材料就是别家的 PPT。
3. **结构最规整**：一页一形状一文本框，能直接映射成 blocks（`slide` 号即 evidence）。

### 为什么图片不能当正经输入
图片里没有结构，只有像素。硬要拆，只能拆出「一块图 + 一句视觉描述」，而这正是 v0.8.1 里**图片计划（slot + 提示词 + 占位）**要解决的事——图片应该走「生成侧」，不是「拆解侧」。所以：图片只做**封面/配图资产**，文字转写归 provider（默认关，界面写清"未配置 OCR / 视觉模型"）。

### 一个反直觉的点
**PDF/PPTX 的"更完整"其实是更危险**：HTML 拆解有明确边界（静态 DOM），而 PDF 的版面是坐标拼出来的，硬还原会得到「看起来像、但结构全错」的 blocks。所以这两个适配器的门禁重点不是"能不能拆"，而是**"拆不出来时有没有如实说"**。

---

## 5. 门禁（每个适配器都要过同一套）

| 门禁 | 判什么 |
|---|---|
| 合同测试 | 每格式一个 fixture（真文件，不是构造的假 XML）：断言 blocks 数量/层级/表格/图片提取 |
| **evidence 完整性** | 100% 的 block 有可回指 locator；抽 3 条按 locator 回原文比对，必须一致 |
| **limitation 真实性** | 对每个声明的限制准备反例（如扫描页 PDF），断言结果里真的出现了该限制、且没有假的正文 |
| 离线路径 | 无网络时全流程可走完；需要 provider 的路径必须明确降级而不是静默吞 |
| 许可 | `origin=user_upload` 走本地文档规则；公开 URL 仍走三档，不得混用 |
| 变异 | 拆掉「写 limitations」或「写 evidence」必须变红（沿用现有变异纪律） |

---

## 6. 落位与顺序

| 版本 | 内容 |
|---|---|
| **v0.8.1**（进行中） | DOCX 解析（已完成）；**把 `DocxOutline` 收敛到 `intake_outline` 契约**（含 evidence：段落序号），提案层直接消费统一形态 |
| v0.8.2 | 界面收敛，不新增适配器（避免又给新界面叠旧问题） |
| **v0.8.3** | `pptx_import.py`（零新依赖）＋ 审核台显示 limitations ＋ 三条合同测试 |
| v0.8.4 / v0.9 | `pdf_import.py`（`[pdf]` extra）＋ 扫描件如实报错；图片作为资产 + 可选 provider |
| 之后 | MCP 工具 `intake_decompose`（复用 HTTP API）＋ CLI 子命令，两端口径一致 |

**估时**：PPTX 读取 0.5–1 天（含门禁）；PDF 文本层 1–1.5 天（扫描件与坐标噪声是主要工作量）；图片 0.5 天（不含 provider）。

---

## 7. 明确不做

- 二进制 / APK / 固件 / 抓包逆向——不是这个产品的问题。
- 自动安装 OCR、PDF、视觉模型的依赖——只提示，不代装（REA 的同一条纪律）。
- 「图片直接拆成页面」——图片只能当资产；结构必须来自文本或模板。
- 把 PDF 的坐标硬还原成 HTML 版式——宁可产出「结构对、样式朴素」，也不产出「看着像、结构错」。

---

## 8. 决定记录（2026-10-18 · KX 已定）

1. **DOCX 收敛到统一契约：已执行。** `htmlninefox/intake_outline.py` 定义 `IntakeOutline / Block / SourceInfo / AdapterInfo`；`docx_import.parse_docx` 现在直接返回它，每个 block 带 `evidence（段落序号）`，顶层带 `limitations`；`validate()` 拒绝没有定位的块。门禁 11 条（`tests/test_docx_import.py`）。
2. **提案层已落地第一版（离线规则）**：`htmlninefox/docx_proposal.py` 产出「意图 ＋ 理由 / 风格预设 ＋ 理由 / 图片计划（slot＋用途＋提示词）/ 可编辑文案 / limitations」，`refiner` 钩子留给 LLM，覆盖结果仍走 `validate()`。门禁 14 条（`tests/test_docx_proposal.py`）。
3. **PPTX 适配器：已排进 v0.8.3**（零新依赖，`python-pptx` 已在导出侧使用；读回 title / bullets / notes 已实测通过）。
