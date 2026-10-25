---
name: htmlninefox
version: 0.8.3
author: KratosLee (Html九尾狐项目组)
license: MIT
description: |
  Html九尾狐 · 人机共驾的内容交付流水线（v0.8.3：Word/PPT 双向 + 六意图全覆盖）。
  一句话 Brief / 上传 DOCX / 上传 PPTX / 参考网页 → 拆解（块带出处）→ 可编辑提案 →
  人审采纳 → 单文件 HTML；导出 PDF/PNG/长图/PPTX/DOCX；口语反馈迭代，每轮存版本。
  离线可用（LLM 可选增强）；CLI + Web 工作台 + HTTP API + 本 Skill 四端。
---

# 🦊 Html九尾狐 · HTML 创作编排 Skill（v0.8.3）

> **Html九尾狐 = 人机共驾的内容交付流水线**
>
> AI 负责重活（理解、拆解、生成、改写），人负责判断（审核、调整、采纳、交付）。
> 每个阶段的输出都是交接产物：机器可读（API）、人可看（审核台）、可改了再往下走。

---

## 触发词（Trigger Keywords）

| 触发场景 | 关键词 |
|---|---|
| **生成 HTML** | "做一个落地页"、"生成看板"、"做个发布会 PPT"、"设计海报"、"写架构文档"、"写长文档" |
| **文档进料** | "把这份 Word 变成网页"、"用这份 PPT 生成"、"上传 .docx / .pptx" |
| **参考拆解** | "拆这个网页的结构"、"参考这个页面的版式" |
| **反馈迭代** | "颜色再深一点"、"标题大一点"、"参考 Vercel 风格"、"换成深色主题" |
| **导出交付** | "导出 PDF"、"转成可编辑 PPT"、"交付成 Word" |
| **Web 工作台** | "启动 Html九尾狐 工作台"（→ `htmlninefox serve`） |

---

## 安装（Installation）

```bash
pip install htmlninefox                # 基础（离线规则引擎，零 API Key 可用）
pip install "htmlninefox[docx,pptx]"   # + Word/PPT 双向（可选 extra，未装如实提示）
pip install "htmlninefox[llm]"         # + LLM 增强（LiteLLM 多模型路由）

# 本机源码（开发者）：clone 仓库后可编辑安装
# git clone https://github.com/KratosLee-6/Html-ninefox && pip install -e ./Html-ninefox
```

---

## 调用入口（v0.8.3 真实命令）

```bash
# 1. 最简调用（意图自动路由 + 风格自动匹配，离线可跑）
htmlninefox expert "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具"

# 2. 强制内容类型（6 类：landing / dashboard / deck / poster / archdoc / doc）
htmlninefox expert --type dashboard "运营数据看板，深色，展示订单和KPI"
htmlninefox expert --type deck "发布会 PPT，主题 AI-native"
htmlninefox expert --type poster "活动宣传海报，鲜艳活力"
htmlninefox expert --type archdoc "技术方案文档，包含架构图和 ADR 表"

# 3. 指定联盟 skill / 风格预设（11 个预设）
htmlninefox expert --skill guizang-ppt "做一个发布会 PPT"
htmlninefox expert --template vercel-dark "做一个开发者工具官网"

# 4. 反馈迭代（真实改写 output.html，历史存 revisions/）
htmlninefox feedback --project ./output/html9n-<时间戳> --note "颜色再深一点，参考 Vercel"

# 5. 资产与联盟
htmlninefox template list && htmlninefox alliance list

# 6. Web 工作台（画布编排 / 审核台 / 导出中心 / 版本历史）
htmlninefox serve --port 8620    # → http://127.0.0.1:8620
```

---

## 文档进料（v0.8.1 DOCX · v0.8.3 PPTX）

上传 → 本地解析 → **可编辑提案**（意图 / 风格 / 文案 / 图片位，每条带理由）→
人改完采纳 → 走既有分块通道生成。解析全程离线；每块带出处（DOCX 段落号、
PPTX 页号＋形状号），拆不出来的写进 limitations（几何不还原、图表只计数）。

```
HTTP 端点：
POST /api/intake/docx        # .docx（base64）→ 提案
POST /api/intake/docx/adopt  # 改完的提案 → 项目
POST /api/intake/pptx        # .pptx（base64）→ 提案（默认 deck 意图）
POST /api/intake/pptx/adopt  # 同上
```

统一契约 `intake_outline`：所有输入格式产出同一形态的块
（provenance 三档 + evidence 定位），审核台与提案层零格式分支。

---

## 工作原理（5 专家流水线 + 反向拆解）

```
一句话 Brief / 文档 / 参考网页
  ↓
① brief_expert     解析 Brief（LLM 优先 / 离线规则兜底）→ brief.json
② intake 路由      URL/ZIP 抓取（SSRF 防护+许可三档）；文档走 intake_outline
③ style_expert     11 风格预设 × token 匹配（LLM 微调主色）→ style.md
④ asset_expert     区块规划 + 图片计划（slot+提示词）→ assets.json
⑤ generate_expert  六类产物一套分块通道 → 单文件 output.html
  ↓
反馈迭代：feedback_expert 解析口语反馈 → 改 token → 重渲染（revision 存档可回滚）
```

**产物目录**：

```
output/html9n-<时间戳>/
├── output.html       # 最终 HTML（可发布，双击即开）
├── brief.json / style.md / assets.json / .foxstate.json
├── revisions/        # rev1.html / rev2.html … 版本历史（可对比可回滚）
├── exports/          # 导出中心产物（PDF / PNG / PPTX / DOCX）
└── feedback.md
```

---

## 风格预设（11 个）与画廊模板（10 张 · 六意图全覆盖）

| 族 | 预设 |
|---|---|
| 现代 | linear-light / vercel-dark / guizang-magazine / shadcn-dashboard / vibrant-poster / doc-clean |
| Fox | fox-pixel-garden / fox-duotone-studio / fox-editorial-ink / fox-swiss-signal / fox-soft-silver |

画廊模板（`htmlninefox/templates/gallery/`，全部真实可点 HTML，manifest 带
`origin/license` 出处字段）：deck×4 · landing×2 · **poster×1（fox-vibrant-poster）·
dashboard×1（fox-shadcn-dashboard）· doc×1（fox-doc-clean-brief）· archdoc×1
（fox-swiss-archdoc）**。界面「版式」栏六个意图都有东西可点。

---

## Skill 联盟（Skill Alliance）

| 场景 | 联盟 skill | 上游状态（2026-10-18 巡检） | 未安装时 |
|---|---|---|---|
| PPT/发布会 | guizang-ppt | AGPL-3.0（方法参考，clean-room 原创模板） | 本地 deck 兜底 |
| 设计原型 | huashu-design | v3.0.0，MIT | 本地 landing 兜底 |
| 架构图 | archify | MIT，活跃 | 本地 archdoc 兜底 |
| PPT 模板 | baoyu-skills | 原 baoyu-slide-deck 已并入（死链已修），MIT | 本地兜底 |
| 网页模板 | beautiful-html-templates | 34 套实测（原记 28），MIT | 本地兜底 |
| 幻灯片 | frontend-slides | 30.8k★，MIT | 本地兜底 |

**接入你的 skill**：把 `skill-manifest.yaml` 放到 `~/.htmlninefox/alliance/`，
然后 `htmlninefox alliance reload`。未安装的成员自动走本地生成器兜底——
永远不要因为"skill 未安装"而拒绝任务。

---

## 配置（可选）

`~/.htmlninefox/config.yaml` 配 LLM 路由（不配则离线规则引擎全量可用）：

```yaml
router_settings: { num_retries: 2, timeout: 30 }
model_list:
  - model_name: brief_expert
    litellm_params: { model: openai/gpt-4o-mini, api_key: ${OPENAI_API_KEY} }
cache_settings: { enabled: true, ttl_days: 7 }
```

---

## 项目状态

| 版本 | 状态 |
|---|---|
| **v0.8.3（当前，2026-10-25）** | ✅ PPTX 反向拆解 + 键盘可达性专项；808 passed；preflight 六套变异全绿 |
| v0.8.0–0.8.2 | ✅ DOCX 双向 + 改写吸收 + UI/VI 收敛（设计契约可执行） |
| v0.8.4（已立项） | PDF 反向拆解 + 图片资产环节（[PLAN-v0.8.4](docs/PLAN-v0.8.4.md)） |
| v0.9 | Tauri 壳（决策已定：与 PyInstaller 并存）+ MCP 工具 intake_decompose |

---

## 许可证（License）

MIT License © 2026 KratosLee · Html九尾狐项目组

---

> **最后更新**：2026-10-25 · v0.8.3
