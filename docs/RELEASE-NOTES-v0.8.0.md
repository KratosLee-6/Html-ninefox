# v0.8.0 发布说明 · DOCX 语义导出 + paraphrased 重新改写

**发布日期**：2026-10-17
**上一版**：v0.7.8（2026-10-17）
**性质**：新能力（v0.8 开篇）。HTTP 新增 `docx` 导出格式与 `retried`
响应字段；项目数据格式不变。规划：`docs/PLAN-v0.8.md`；北极星：
`docs/VISION.md`。

---

## 一句话

**导出矩阵补上 Word 这一格（v0.4 设计文本预告的最后一格）：doc/archdoc
全文语义映射、deck 讲义、降级清单如实上市；审核台新增拆块预览面板，
paraphrased 块可一键「重新改写」——预览即所得的显式重试。**

---

## Added · DOCX 语义导出

- **doc/archdoc → 全文语义版**：h1–h6 → Heading 1–6、段落、ul/ol 列表、
  表格（Table Grid）、data: URI 内嵌图片（含 alt 题注）、引用、hr 分隔
  线、pre/code 等宽段落。文档元数据带标题。
- **deck → 讲义式大纲**：每页一个二级标题 ＋ 要点列表（复用 PPTX 页解析，
  扁平化清单如实随行）。
- **视觉型产物如实引导**：landing/poster/dashboard 选 Word 导出得 400
  （`docx_intent_unsuited`）——引导 PDF/PNG 高保真路径，而不是给一份
  错形的 Word。导出中心选项按意图显隐，原因可读。
- **降级清单如实上市**：外链图片不抓取（离线承诺）、CSS 配色/字体/布局
  不映射、非语义容器文本计数上报、界面 chrome 单独计数不混入正文——
  每一项都有门禁盯住「声称丢弃的真不在文档里」。
- 依赖：`python-docx` 进可选 extra `[docx]`（未装如实提示 pip 命令；
  dev extra 同步纳入，CI 深度回读必跑）。标准库 zip 冒烟路径永不跳过。

## Added · paraphrased「重新改写」

- `/api/intake/page-blocks` 新增 `retry_paraphrase: true`：绕过 LLM 缓存
  重新改写（`retrying()` 包装——缓存感知判定用签名，不靠 TypeError），
  响应带 `retried` 标记。
- 审核台已采纳候选新增**拆块预览面板**：每块的 provenance 徽标（原文/
  改写/仅结构）＋ 内容预览；面板内一键「🔄 重新改写」。未配置 LLM 或
  改写未过忠实度时如实提示。

---

## 门禁

| 门禁 | 拦什么 |
|---|---|
| `test_docx_export.py`（9 条） | 回读逐项断言（标题层级/列表样式/引用/表格/内嵌图/代码块）；**降级清单完整性**（三边一致：源数量 == 报告计数 == 回读计数；声称丢弃的真不在）；deck 讲义回读；意图守卫 400；pip 提示；zip 冒烟；选项登记 |
| paraphrased 门禁扩至 12 条 | retrying 绕缓存；无缓存缝改写器如实透传；service retried ＋ 绕缓存；未配置时重改如实回落 |
| 真链验收 **18/18** | 重改：retried 如实、改写仍随行 |
| 变异 | docx 3/3（表格映射拆/降级说谎/意图守卫拆）；paraphrased 5/5（含重改包装被拆） |
| 内容标记 | 冻结包伺服页面新增 `DOCX` 断言（双验证器），陈旧产物发布回读时被抓住 |

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **685 passed / 4 skipped**（含本轮新增 9 条 docx 门禁 ＋ 4 条重改门禁；4 处旧断言随格式矩阵扩张同步更新） |
| 真链验收 | 18/18 PASS |
| 变异验证 | docx 3/3 ＋ paraphrased 5/5 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.8.0 一致 |

---

## 明确不在这一版

- **DOCX 导入 ＋ AI 理解补全**：v0.8.1 主打（`docx_outline` →
  `docx_proposal` 落审核台），见 `docs/PLAN-v0.8.md`。
- 图像模型自动接入（图片计划的直出 Provider）：独立决策点。
- 键盘可达性专项、Tauri 桌面壳：v0.8.2（Tauri 两个决策点定案后动工）。
