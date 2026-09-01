# Html九尾狐 · v0.3.0 Beta 2「跨平台可安装版」

> **开源 HTML 创作 Skill 联盟主编排器**
> 一句话 Brief → 6 内容类型 × 11 风格预设 → 单文件可发布 HTML；
> 反馈迭代 = 改设计 token 重渲染；CLI / Web / PWA / Claude Code Skill 多端；**离线可用**（LLM 可选增强）。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![Status: v0.3.0b2](https://img.shields.io/badge/status-v0.3.0b2-blue.svg)]()

---

## 安装

```bash
pip install -e .              # 基础版：离线规则引擎，零 API Key 可用
pip install -e ".[llm]"       # + LLM 增强（LiteLLM 多模型路由）
pip install -e ".[dev]"       # + 测试工具
```

依赖：`pyyaml / click / rich`（必装，轻量）；`jinja2 / litellm`（可选增强）。

---

## v0.3.0 Beta 2 · 真实模板与 AI 编排

- 新增 6 套可独立打开的真实 HTML 模板作品，共 35 个可预览、可抽取页面，覆盖归藏电子墨水、靛蓝研究、瑞士信号、牛皮纸叙事、沙丘作品集和像素花园产品页。
- “版式 / 内容 / 风格”全部优先展示真实 iframe 效果；模板可查看完整页面序列，单页可直接抽取到工作区继续组合。
- 顶部新增“输入需求”：统一接收文字、文档与图片，执行“分析 → 推荐组合 → 默认生成 / 自定义编排”双路径。
- 工作区推进现在真实消费所选模板、页面 blocks、色卡、字体、文件、技能与附件上下文，并写入项目 `.foxstate.json`。
- 顶部新增“AI 模型”：支持用户配置 OpenAI-compatible API Base、模型名和 API Key；Key 仅本地保存且读取接口不返回明文。
- 未启用 AI 或模型不可用时继续使用离线规则引擎，不阻塞生成。

## v0.3.0 Beta 2 跨平台可安装版

- 新增 `htmlninefox app`：自动选择可用端口、等待服务就绪并打开浏览器。
- Windows 提供内置 Python 运行时的便携 ZIP，并提供 Inno Setup 安装器定义。
- Linux 提供用户级自解压 `.run` 与审计友好的 `.tar.gz`。
- 新增 uv、Docker Compose、PWA、局域网共享等免传统安装运行方式。
- Windows 便携版将配置、缓存和产物统一放入包体旁的 `user-data/`。
- 新增 Windows / Linux 自动打包工作流与 SHA256 校验文件。

## v0.2.5 像素花园品牌工作台

- 正式采用 A「像素花园」方向：深钴蓝、薄荷绿、暖纸白与细像素识别。
- 新增可编辑 SVG 品牌符号、横版 Logo 与 PWA 图标，融合九尾狐和 HTML 尖括号。
- 工作台默认改为暖纸白主题，可一键切换夜蓝主题；偏好自动保存。
- 圆角、阴影、字体、网格、焦点态、节点与工作区统一为 Pixel Garden UI 语言。
- 首次创建的示例工作区默认使用 `fox-pixel-garden`，不再默认黑紫模板。
- 完整规范见 [VI 手册](docs/VI.md) 与 [UI 手册](docs/UI-GUIDE.md)。

## v0.2.4 工作区管理与多风格系统

- 新增工作区列表、定位、重命名、独立颜色与当前工作区进度；无限画布不再依赖人工寻找。
- 工作区可从标题栏或空白区域整体拖动，内部素材保持相对位置；旧快照自动补齐工作区归属。
- 新增 5 套原创视觉系统，合计 11 套风格，并在 6 类内容中呈现结构级真实 HTML 差异。
- 画布继续采用统一世界坐标与 `requestAnimationFrame` 热路径；拖动期间不反复写入快照。
- 节点支持 16px 网格、同边/中心对齐辅助线；按住 `Alt` 可临时关闭吸附。
- 连线改为左右输入/输出端口，扩大命中半径，并在松手前高亮候选端口。
- 6 类版式与 11 套风格直接渲染真实 HTML 缩略图，可一键放大或新窗口查看。
- 项目支持重命名、创建副本和可恢复软删除（输出目录 `.trash`）。
- Canvas Schema v1 同时保存到 localStorage 与服务端原子快照；主快照损坏时自动读取备份。
- 生成改为持久化 Job：`queued / running / succeeded / failed / cancelled`，工作台轮询展示进度。
- 所有 HTTP 错误统一返回 `error.code / error.message / request_id`。
- 顶部“诊断”可下载脱敏 zip；不包含 API Key 值、完整 Prompt、HTML、Brief 或反馈内容。

## 多端用法

### ① CLI

```bash
htmlninefox expert "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具"
htmlninefox expert --type deck "发布会 PPT，主题 AI-native"      # 6 类内容可选
htmlninefox expert --template vercel-dark "开发者工具官网"        # 11 风格预设可选
htmlninefox feedback --project output/html9n-<时间戳> --note "颜色再深一点，标题大一点"
htmlninefox brief list | template list | alliance list
```

### ② Web 工作台（无限画布 · 工作区编排）

```bash
htmlninefox serve          # http://127.0.0.1:8620
```
**工作区编排模式（默认 `/`）**：
- **真实可视化素材库**：6 类版式与 11 套风格直接显示真实 HTML 缩略图；内容块、色卡、字体与历史文件继续图形化展示，可放大预览后再拖入画布
- **工作区**：画布上的可调大小框；拖入 版式/风格/色卡/字体/内容块 = 你的专属模板配方；`⤢ 适配` 一键自动缩放（HUD 也有全局适配）
- **推进流水线**：往工作区拖入一个「需求」节点 → 点 `▶ 推进` → 自动拆解需求（类型/风格/要点 chips）→ 自动组合工作区素材 → 产物节点落到工作区右侧并自动连线、全景缩放
- **反馈迭代**：选中产物节点在检查器提交口语反馈，改 token 重渲染（rev 历史）
- 经典表单版在 `/classic`；画布状态自动持久化

#### 安装为桌面 / 移动端应用（PWA）

- Windows / macOS：用 Edge、Chrome 或 Safari 打开工作台，点击顶部“安装”。
- iPhone / iPad：部署到 HTTPS 后，用 Safari 打开，选择“分享 → 添加到主屏幕”。
- 手机与平板：素材库、检查器改为抽屉；素材支持点按加入；画布支持触控平移与拖动。
- 离线时可继续编辑已加载的工作区；生成、反馈和项目列表仍需连接 Html九尾狐本地服务或云端服务。

可通过 `GET /api/capabilities` 获取当前客户端与能力状态，供未来 Windows/macOS/iOS 客户端复用。

### ③ Claude Code Skill

见 [`SKILL.md`](SKILL.md)（与 v0.3.0 Beta 2 命令一致）。

---

## 多内容（6 类生成器）与多风格（6 预设）

> 优先级对齐实际使用：**以 HTML 为载体的 PPT / 文档 / 单页在前，网站类在后**。

| 内容 | intent | 生成器 | 产物 |
|---|---|---|---|
| 发布会 PPT | `deck` | `generators/deck.py` | 横向翻页（←/→ 键） |
| 文档 | `doc` | `generators/doc.py` | 报告/方案/纪要（摘要/章节/里程碑/结论） |
| 海报/一页纸 | `poster` | `generators/poster.py` | 单屏大字报 |
| 落地页 | `landing` | `generators/landing.py` | Hero/特性/定价/FAQ 营销页 |
| 数据看板 | `dashboard` | `generators/dashboard.py` | KPI 卡 + CSS 图表 + 表格 |
| 架构文档 | `archdoc` | `generators/archdoc.py` | 分层图 + 组件表 + 决策 |

风格预设（`generators/_tokens.py`，CSS 变量驱动）：`linear-light` / `vercel-dark` /
`guizang-magazine` / `shadcn-dashboard` / `vibrant-poster` / `doc-clean`。
反馈迭代只改 token（`_tokens.apply_feedback`），生成器零改动。

---

## 产物结构

```
output/html9n-<时间戳>/
├── output.html       # 单文件可发布 HTML（双击即开）
├── brief.json / .md  # Brief 标准 v0.1（LLM 优先 / 离线规则兜底）
├── style.md          # 风格 token 表
├── assets.json       # 区块规划
├── .foxstate.json    # 迭代状态（反馈重渲染依据）
├── revisions/        # rev1.html / rev2.html …
└── feedback.md       # 反馈沉淀
```

---

## Skill 联盟

- 内置 manifest：`htmlninefox/data/alliance/`（guizang-ppt / huashu-design / archify）
- 接入你的 skill：把 `skill-manifest.yaml` 放到 `~/.htmlninefox/alliance/` → `htmlninefox alliance reload`
- 未安装的联盟 skill 自动走本地生成器兜底（`fallback: local:<intent>`），永不空转

## 审美模板贡献

参考 `examples/`；模板 = 一个目录 + `style.json`（token 表）+ 可选 `README.md`：

```json
{ "name": "我的品牌风", "dark": true,
  "tokens": { "bg": "#101010", "primary": "#FF5A00", "...": "..." } }
```

放到 `~/.htmlninefox/templates/<模板ID>/style.json` → `htmlninefox template list` 立即可见；
`htmlninefox expert --template <模板ID>` 直接使用。

---

## 测试与验收

```bash
python -m pytest tests/ -q      # 102 例：核心/CRUD/恢复/Job/诊断/API/PWA
python e2e_verify.py            # 14 项端到端验收 + 截图（e2e-shots/）
```

---

MIT License © 2026 KratosLee · Html九尾狐项目组
