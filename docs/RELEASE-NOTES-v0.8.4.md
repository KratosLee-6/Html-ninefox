# v0.8.4 · 贴入 PDF + 图片资产

**发布日期**：2026-10-29
**主题**：反向拆解矩阵再进一格式——**一份 PDF 走 Word/PPT 同一条管线**（只信
文本层、扫描页如实上报）；**图片位可以挂真实图片**了（检查摘要回填、附图入库
参与生成）；联盟接入设计质量层 impeccable。

---

## 一、PDF 反向拆解

上传 .pdf → `pdf_import`（`[pdf]` extra，pdfminer.six 纯 Python）→ 统一
`intake_outline` → 提案 → 审核台（同一张界面）→ 采纳生成。HTTP 新增
`/api/intake/pdf(+/adopt)`。

| 能拿到 | 如实说拿不到（limitations，UI 可见） |
|---|---|
| 页题→标题（字号推断，规则随附）、正文→段落、表格压平说明 | **版面/表格结构不还原**——宁「结构对、样式朴素」 |
| evidence＝页号＋页内字符区间，100% 可回指 | **无文本层的页如实报「可能为扫描件」**，不 OCR 硬猜 |

## 二、图片位挂真实资产（收口项）

审核台每个图片位可附 PNG/JPEG：检查接口回填尺寸/主色摘要 chip；采纳时附图
经 `slot_images` 入库为真实输入素材、**参与本次生成**；`ImagePlanItem` 增可选
`asset` 摘要字段（机器契约向后兼容），payload 回显 `slot_attachments` 与
`proposal.image_plan[].asset`。三格式 adopt 端点同构。

## 三、图片资产检查

`image_assets.py`：PNG/JPEG 尺寸格式用 stdlib 解析（零依赖）；主色走
`[image]` extra（Pillow），**两级降级如实标注**（无 Pillow / 像素损坏）。
OCR/视觉转写维持 provider 决策默认关。HTTP 新增 `/api/intake/image`。

## 四、审核台与模板

- 图片位 UX：槽位名默认中文（封面主视觉/章节配图 N）+ 一键 EN 切换（手改名
  不被覆盖）；编辑区卡片化 + 可编辑提示；边界清单 Callout 化
- 模板库 A 档：画廊 6 → **10 张，六意图全覆盖**（新增 poster/dashboard/
  doc/archdoc 各一张原创模板）；manifest 全体带 `license` 出处字段
- 修复 recommend 跨意图推荐 bug（doc/poster/dashboard/archdoc 曾兜到 deck 模板）

## 五、设计质量层 · impeccable 接入（联盟）

`pbakaus/impeccable`（88.7k★ · Apache-2.0 · AI 前端设计质量层：62 条确定性
检测规则 + 24 命令）注册为联盟成员——装了它的用户可在生成产物上直接跑
`audit/critique` 体检；**未安装照旧本地兜底，能力不缺失**。评估与路径见
`docs/EVAL-impeccable-20261027.md`。

## 六、门禁与证据

| 门禁 | 数字 |
|---|---|
| PDF 解析合同 | 10 条（locator 回源切片、扫描页上报、字号推断、魔数校验） |
| PDF API | 13 条（六意图真链） |
| 图片资产 | 5 + 2 条（含降级如实标注、端点拒绝） |
| 图片位挂图 | 附图真链 + 垃圾拒绝（本轮新增） |
| 变异 | `mutate_pdf_gates` 4/4 CAUGHT，**preflight 七套全绿** |
| 全量 | **847 passed / 4 skipped**（2026-10-29 实测） |

开发中被门禁抓到的真问题：pdfminer 行对象藏在 LTTextBox 子级（首版收集器
永远空集）；手写 PDF fixture 的 /Length 写死会静默产出 0 页；间距 burn-down
门禁拦下新增裸间距（改走令牌）。

## 七、升级说明

- 无数据迁移：工作区、产物、导出格式、项目数据格式都不变
- 新增可选 extra：`[pdf]`（pdfminer.six）、`[image]`（Pillow）——未装时如实
  提示并降级，离线承诺不破
- 联盟新成员 impeccable 的探测走 PATH 启动器（`detect_bin`），路由入口白名单
  相应放开 `npx ` 前缀（安全策略：入口仍禁止 shell 元字符）
