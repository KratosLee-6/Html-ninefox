# Agent 调用指南 · Html九尾狐

> **读者**：想让 AI / agent 驱动 Html九尾狐 的开发者和智能体。
> **纪律**：本文所有命令与回显均为 **2026-10-26 在 v0.8.3 真实环境实跑采集**，
> 不是示意代码。版本迭代后以 `htmlninefox version` 的实测输出为准。

---

## 0. 一句话与能力总览

Html九尾狐是一条**人机共驾的内容交付流水线**：AI 做重活（理解、拆解、生成、
改写），人做判断（审核、调整、采纳）。对 agent 而言，它是一个**本地优先的
HTML 生成与文档反拆服务**——每个阶段的输出既是 JSON 交接物，也是人可审核
的界面，agent 可以驱动全程。

| 维度 | 能力 |
|---|---|
| 进料（4 种） | 一句话需求 · 上传 .docx · 上传 .pptx · 参考网页/ZIP 拆解（v0.8.4 起 +.pdf） |
| 产物（6 意图） | landing / deck / poster / dashboard / doc / archdoc |
| 交付（5 格式） | 单文件 HTML · PDF · 长图 · 逐页 PNG · 可编辑 PPTX/DOCX |
| 风格 | 11 预设 × 10 张画廊模板（六意图全覆盖） |
| 运行形态 | Web 工作台 · CLI · Windows/macOS/Linux 桌面包 · Docker · HTTP API |
| 离线承诺 | 不配 LLM 走规则引擎全量可用；LLM 是增强不是依赖 |

---

## 1. 通路一 · CLI（agent 能开终端就能用）

**安装**（一次）：

```bash
pip install htmlninefox                 # 基础（离线可用）
pip install "htmlninefox[docx,pptx,pdf]"  # + Word/PPT/PDF 进出（可选 extra）
```

**实测**（v0.8.3，规则引擎，未配任何密钥）：

```bash
$ htmlninefox version
🦊 Html九尾狐 v0.8.3 · MIT License

$ htmlninefox expert "做一个本地优先内容交付工作台的落地页，品牌「狐构」，面向设计团队" \
    --type landing --quiet-llm
✓ 已生成
…/output/html9n-2026-10-26-210540/output.html
# 产物目录：output.html + brief.json/style.md/assets.json + recipe-run.json + revisions/

$ htmlninefox feedback --project output/html9n-2026-10-26-210540 --note "标题大一点，配色更稳重"
规则: color_shift, font_up   模型: rules
# → revisions/rev1.html（真实改写，可回滚）

$ htmlninefox export output/html9n-2026-10-26-210540 --format pdf
…/exports/20261026-210553-865fcd/document.pdf + export-report.json
```

**子命令速查**（`--help` 看全参）：`expert`（一句话生成）· `feedback`（口语迭代）
· `export`（PDF/PNG/PPTX/DOCX）· `serve`/`workbench`/`app`（工作台）·
`template`（列预设）· `alliance list`（联盟状态）· `brief` · `restore` · `version`。

> 注意：`template` 是独立命令，**没有** `list` 子参数——直接 `htmlninefox template`。

---

## 2. 通路二 · HTTP API（agent 最强入口，全流程可驱动）

起服务：`htmlninefox serve --port 8620`（默认仅本机；**无鉴权，勿直接暴露公网**）。

### 2.1 一句话 → 分析

```bash
curl -s -X POST http://127.0.0.1:8620/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt":"做一个 AI 产品发布会页面，面向设计团队，本地优先"}'
```

实测回显（节选）：

```json
{"intent": "deck", "intent_confidence": 0.55, "engine": "rules",
 "preset_id": "vercel-dark", "headline": "AI 产品发布会页面"}
```

### 2.2 生成

`POST /api/generate`（同步）或 `POST /api/jobs`（异步长任务）。核心字段：
`prompt` / `intent` / `template`（预设）/ `blocks`（分块，可全自定义）/
`content`（caller-owned 文案：headline、summary 等）/ `quiet_llm`。
返回 `project_name` + `preview_url` + `verification`（质量检查）+ `recipe_run`（时间线审计）。

### 2.3 文档进料（DOCX / PPTX / PDF 共用契约）

```python
import base64, json, urllib.request
def post(path, body): ...
b64 = base64.b64encode(open("方案.docx", "rb").read()).decode()

p = post("/api/intake/docx", {"name": "方案.docx", "docx_base64": b64})
# p["proposal"]：意图/风格/文案/图片位，每条带理由；人可改任何字段
# p["limitations"]：解析边界（如实说明拿不到什么）
a = post("/api/intake/docx/adopt", {"name": "方案.docx", "docx_base64": b64,
         "proposal": {"intent": "deck"}})   # 改完采纳 → 走既有生成通道
# a["project_name"] / a["verification"]["ok"]
```

实测回显（2026-10-26）：`意图: doc | evidence_complete: True`；
采纳后 `verification.ok: True`，产物落盘可导出。PPTX/PDF 端点同构
（`/api/intake/pptx(+/adopt)`、`/api/intake/pdf(+/adopt)`，字段 `pptx_base64` / `pdf_base64`）。

### 2.4 图片资产检查（v0.8.4）

```python
post("/api/intake/image", {"image_base64": b64})
# → {"format":"png","width":30,"height":10,"bytes":87,
#    "dominant_color":"#243E8F","color_source":"pillow"}
# 无 Pillow 时 dominant_color 缺席，color_source 说明原因（降级如实标注）
```

### 2.5 其余常用端点

`GET /api/projects` · `GET /api/health` · `GET /api/capabilities`（35 项能力声明）
· `POST /api/feedback` · `GET /api/exports/capabilities` · `POST /api/exports`
· 修订：`GET /api/projects/<名>/revisions`、`POST …/restore-revision`。

---

## 3. 通路三 · Skill 文件（给对话式 agent 的说明书）

仓库根 `SKILL.md` 与 `skill/SKILL.md` 是 agent 可直接加载的操作手册
（触发词 / 命令 / 故障速查）。安装到你的 agent：

```bash
# Claude Code / 兼容 agent：把仓库的 SKILL.md 放进技能目录
git clone https://github.com/KratosLee-6/Html-ninefox
mkdir -p ~/.agents/skills/htmlninefox
cp Html-ninefox/SKILL.md ~/.agents/skills/htmlninefox/SKILL.md
```

之后用户说「做一个落地页」「把这份 Word 变成网页」时，agent 按手册把需求
翻译成上面的 CLI/API 调用。触发词全表见 `SKILL.md`。

---

## 4. 通路四 · 联盟（反向：被别的 skill 编排）

Html九尾狐自己是**编排器**：`~/.htmlninefox/alliance/` 里放其他 skill 的
`skill-manifest.yaml`，`htmlninefox alliance reload` 后即可路由。当前 6 成员
（archify / baoyu / beautiful-html-templates / frontend-slides / guizang / huashu），
**未安装的成员自动走本地生成器兜底**——能力不缺失，只降级，且降级如实标注。
上游状态经巡检记录在各成员 yaml 的 `upstream_*` 字段（2026-10-18 核验）。

---

## 5. 机器契约要点（agent 依赖的稳定形状）

| 契约 | 字段 | 纪律 |
|---|---|---|
| `intake_outline` | blocks[].`provenance`（verbatim/paraphrased/structure_only）+ `evidence`（DOCX 段号；PPTX 页号+形状号；PDF 页号+字符区间） | 无定位的块**拒绝进审核台**——agent 引用任何块都能回指原文 |
| `proposal` | intent / style（带 reason）/ copy / image_plan / limitations | 人可改；`adopt` 时服务端 `validate()` 兜底，坏提案 400 |
| `limitations` | 每份拆解必带 | 「拿不到什么」是交付物：几何不还原、扫描页、图表只计数都写在这 |
| `recipe_run` | 阶段时间线 | agent 审计「这次生成发生了什么」的依据 |
| slot 命名 | 机器层 `cover`/`section-N` 英文契约 | 中文是**展示层翻译**（审核台），API 形态不变 |

---

## 6. 常见任务速查

| agent 任务 | 最短调用 |
|---|---|
| 一句话出页 | `htmlninefox expert "<需求>"` 或 `POST /api/generate` |
| Word/PPT/PDF → 网页 | `POST /api/intake/<格式>` → 人改 → `…/adopt` |
| 口语改稿 | `htmlninefox feedback --project <dir> --note "<反馈>"` |
| 交付 PDF/PPT/Word | `htmlninefox export <dir> --format …` |
| 查产物能不能回指原文 | 读 `blocks[].evidence` + `limitations` |
| 看这次生成分了几步、每步多久 | 读产物目录 `recipe-run.json` |
| 判断当前环境有哪些能力 | `GET /api/capabilities` |

---

## 7. 边界与红线（agent 必读）

1. **不做后端**：表单提交、数据库连接不在范围；产物是静态单文件。
2. **无鉴权**：`serve` 默认只绑 127.0.0.1；要局域网/公网必须自备反向代理与认证。
3. **OCR/视觉转写默认关**：图片只有尺寸与主色，文字转写是 provider 决策。
4. **参考抓取只允许公网**：SSRF 防护拒绝私网地址；许可三档（open/reference/
   inspiration-only）决定正文是否随行。
5. **可选依赖如实提示**：`[docx]`/`[pptx]`/`[pdf]`/`[image]` 未安装时返回
   明确的 pip 提示，不会静默失败，也不会偷偷安装。

---

## 8. 路线

- **v0.8.4（进行中）**：PDF 反向拆解（本文 2.3 即可调用）与图片资产已落地；
  审核台图片位挂真实资产的 UI 收尾中。
- **v0.9**：MCP 工具 `intake_decompose`（agent 无需写 HTTP 也能发现并调用）；
  Tauri 桌面壳（与 PyInstaller 并存）。
- 相关文档：[VISION.md](VISION.md)（北极星）·
  [DESIGN-REVERSE-INTAKE.md](DESIGN-REVERSE-INTAKE.md)（反拆契约）·
  [PLAN-v0.8.4.md](PLAN-v0.8.4.md)（当前版本计划）。
