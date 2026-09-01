---
name: htmlninefox
version: 0.2.4
author: 汐构科技 (Html九尾狐 项目组)
license: MIT
description: |
  Html九尾狐 · HTML 创作 Skill 联盟主编排器（v0.2.4 工作区管理与多风格系统）。
  一句话 Brief → 5 内容类型（落地页/看板/PPT/海报/架构文档）× 11 风格预设，
  联盟路由 guizang-ppt / huashu-design / archify；反馈迭代 = 改设计 token 重渲染。
  离线可用（LLM 可选增强）；CLI + Web 工作台 + 本 Skill 三端。
---

# 🦊 Html九尾狐 · Claude Code Skill（v0.2.4）

> **Html九尾狐 = 一个开源的 HTML 创作专家 Skill 联盟主编排器**
>
> 你写一句话 Brief → 5 专家流水线（Brief/Style/Asset/Generate/Feedback）→
> 单文件可发布 HTML；反馈迭代改 token 重渲染，经验沉淀到三库。

---

## 触发词（Trigger Keywords）

| 触发场景 | 关键词 |
|---|---|
| **生成 HTML** | "做一个落地页"、"生成 Dashboard"、"做个发布会 PPT"、"设计海报"、"写架构文档" |
| **联盟路由** | "用 guizang 做 PPT"、"用 huashu 做设计原型"、"用 archify 做架构图" |
| **反馈迭代** | "颜色再深一点"、"字号大一点"、"参考 Vercel 风格"、"换成深色主题" |
| **模板复用** | "用 vercel-dark 预设"、"列出可用模板" |
| **Web 工作台** | "启动 Html九尾狐 工作台"（→ `htmlninefox serve`） |

---

## 安装（Installation）

```bash
pip install htmlninefox              # 基础（离线规则引擎，零 API Key 可用）
pip install "htmlninefox[llm]"       # + LLM 增强（LiteLLM 多模型路由）
```

---

## 调用入口（v0.2.4 真实命令）

```bash
# 1. 最简调用（意图自动路由 + 风格自动匹配，离线可跑）
htmlninefox expert "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具"

# 2. 强制内容类型（6 类）
htmlninefox expert --type dashboard "运营数据看板，深色，展示订单和KPI"
htmlninefox expert --type deck "发布会 PPT，主题 AI-native"
htmlninefox expert --type poster "活动宣传海报，鲜艳活力"
htmlninefox expert --type archdoc "技术方案文档，包含架构图"

# 3. 指定联盟 skill / 风格预设
htmlninefox expert --skill guizang-ppt "做一个发布会 PPT"
htmlninefox expert --template vercel-dark "做一个开发者工具官网"

# 4. 反馈迭代（真实改写 output.html，历史存 revisions/）
htmlninefox feedback --project ./output/html9n-<时间戳> --note "颜色再深一点，参考 Vercel"
htmlninefox feedback --project ./output/html9n-<时间戳> --note "标题大一点" --dry-run

# 5. 三库管理
htmlninefox brief list && htmlninefox brief show <id>
htmlninefox template list
htmlninefox alliance list

# 6. Web 工作台（工作区编排：全可视化素材 → 需求自动拆解组合 → 产物预览/迭代）
htmlninefox serve --port 8620
```

---

## 工作原理（5 专家流水线）

```
一句话 Brief
  ↓
① brief_expert   解析五字段 Brief（LLM 优先 / 离线规则兜底）→ brief.json
② alliance 路由  意图分类（landing/dashboard/deck/poster/archdoc）→ 联盟 skill 或本地
③ style_expert   11 风格预设 × token 匹配（LLM 微调主色）→ style.md
④ asset_expert   按内容类型规划区块 → assets.json
⑤ generate_expert 生成单文件 HTML（CSS 变量驱动，零外部依赖）→ output.html
  ↓
反馈迭代：feedback_expert 解析口语反馈 → 改 token → 重渲染（.foxstate.json 驱动）
```

**产物目录**：

```
output/html9n-<时间戳>/
├── output.html       # 最终 HTML（可发布，双击即开）
├── brief.json / brief.md   # Brief 标准 v0.1
├── style.md          # 风格 token 表
├── assets.json       # 区块规划
├── .foxstate.json    # 迭代状态（反馈重渲染的依据）
├── revisions/        # rev1.html / rev2.html … 迭代历史
└── feedback.md       # 反馈沉淀
```

---

## LLM Agent 使用指引（无 CLI 环境时）

如果没有 CLI，按以下约定直接产出等价物：

1. **意图分类**：从用户需求判断内容类型（关键词：落地页/官网→landing；看板/后台→dashboard；
   PPT/发布会→deck；海报→poster；架构/技术方案→archdoc）
2. **风格预设**：从 6 预设选择——linear-light（极简浅色）/ vercel-dark（深色极客）/
   guizang-magazine（杂志衬线）/ shadcn-dashboard（数据看板）/ vibrant-poster（活力海报）/
   doc-clean（专业文档）；生成器源码见包内 `htmlninefox/generators/`
3. **产物要求**：单文件 HTML、UTF-8、viewport meta、无外部依赖、颜色用 CSS 变量
   （--fox-bg/--fox-primary/--fox-text…）以便后续 token 迭代

---

## Skill 联盟（Skill Alliance）

| 场景 | 联盟 skill | 作者 | v0.2 状态 |
|---|---|---|---|
| PPT/发布会 | guizang-ppt | 归藏 | manifest 已内置，未安装时本地 deck 兜底 |
| 设计原型 | huashu-design | 花叔 | manifest 已内置，未安装时本地 landing 兜底 |
| 架构图 | archify | tt-a1i | manifest 已内置，未安装时本地 archdoc 兜底 |
| 配图插画 | （招募中） | - | 欢迎提交 manifest |

**接入你的 skill**：把 `skill-manifest.yaml` 放到 `~/.htmlninefox/alliance/`：

```yaml
name: your-skill
version: 1.0.0
category: deck                 # landing/dashboard/deck/poster/archdoc
intents: [deck]
python_module: your_skill      # 可 import 即视为已安装
entry: python -m your_skill --topic "{topic}"
fallback: local:deck           # 未安装时的本地兜底
```

然后 `htmlninefox alliance reload`。

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

三库位置（自动创建）：`~/.htmlninefox/{briefs,templates,feedback,styles,cache,logs}`

---

## 项目状态

| 版本 | 状态 |
|---|---|
| **v0.2.4（当前）** | ✅ 丝滑画布 + 真实 HTML 模板预览 + 可恢复工作台；CLI / Web / PWA / Skill 可用 |
| v0.3（Month 3-6） | 联盟 skill 真实接入（guizang/huashu/archify 上游）+ 模板市场 + 飞书 aily |
| v1.0（Month 12） | 5K Star · 100 种子开发者 · 社区驱动飞轮 |

---

## 许可证（License）

MIT License © 2026 汐构科技 · Html九尾狐 项目组

---

> **最后更新**：2026-08-31 · v0.2.4
