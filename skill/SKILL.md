---
slug: kratoslee-htmlninefox
displayName: Html九尾狐·HTML创作工作台
version: 1.2.0
summary: 人机共驾的内容交付流水线：一句话 / Word / PPT / 参考网页进料 → 带出处的拆解 → 可编辑提案 → 人审采纳 → 零依赖单文件 HTML → 导出 PDF / PNG / 长图 / 可编辑 PPTX / DOCX。
license: MIT
author: KratosLee
name: htmlninefox
description: |
  Html九尾狐 = 人机共驾的内容交付流水线。文字、Word、PPT、网页模板都能进料，
  AI 拆解并给出可编辑提案（意图/风格/文案/图片位，每条带理由），人审采纳后生成
  真正可交付的单文件 HTML；口语反馈迭代，每轮存版本可回滚；导出 PDF / PNG /
  长图 / 可编辑 PPTX / DOCX。全程本地，离线可用。
  触发：做单文件 HTML / 网页海报 / 落地页 / 发布会 PPT / 数据看板 / 架构文档 /
  把 Word 或 PPT 变网页 / 导出 PDF 或 Word。
tags: [html, canvas, workbench, pdf-export, single-file-html, kratoslee]
---

# 🦊 Html九尾狐 · HTML 创作工作台

> 让灵感在 HTML 里生长 · v0.8.3 · 个人开源 MIT · 简体中文

---

## 触发场景

当用户出现以下任一诉求时，加载并执行本 Skill。

| 用户想做什么 | Agent 该跑什么 |
|---|---|
| 「做一个单文件 HTML」「零依赖网页」 | `htmlninefox expert "<需求>"` |
| 「做张网页海报」「做个落地页」「做发布会 PPT」「做数据看板」「做架构文档」 | `expert --type poster/landing/deck/dashboard/archdoc/doc` |
| 「把这些素材组合成一个页面」「在画布上排版」 | `htmlninefox workbench` → 画布工作流 |
| 「导出 PDF」「导出 PNG」「发长图给客户」 | `htmlninefox export <项目>` |
| 「标题大一点」「颜色再稳重一些」 | `htmlninefox feedback --project <项目> --note "<反馈>"` |
| 「记住我喜欢深蓝」「下次还用这个模板」 | Project Memory（产物检查器 → 采用此版本并学习） |
| 「把这份 Word 变成网页」「用这份 PPT 生成」 | 审核台上传 → 提案 → 采纳（HTTP `/api/intake/docx|pptx`） |

**已在范围内（v0.8 起）**：原生 Word / PPTX 进料（审核台出提案）与可编辑 DOCX / PPTX 导出。仍不在范围：后端服务（表单提交、数据库）。

---

## 30 秒快速上手

```bash
# 1. 安装（零 API Key 也能跑，离线规则引擎兜底）
pip install htmlninefox
# Windows 用户可双击 install-and-run-windows.cmd
# 服务器/NAS：docker compose up --build

# 2. 启动 Web 工作台（默认端口 8620，被占用时自动顺延 8621/8622…）
htmlninefox workbench

# 3. 浏览器打开 http://127.0.0.1:8620
```

可选 AI 增强（不配也能生成）：
环境变量 `MINIMAX_API_KEY` → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` 按优先级生效，
或在工作台里打开「AI 配置」写入输出目录的 `.settings/ai.json`（仅本地，Key 不进项目快照）。

---

## 三条核心工作流

### ① 文字 → 分析 → 推荐 → 生成

```bash
htmlninefox expert "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具"
htmlninefox expert --type deck --template guizang-magazine "AI 产品发布会 PPT"
htmlninefox expert --type dashboard --quiet-llm "运营数据看板，深色，展示订单和 KPI"
```

流水线：`Analyze → Compose → Generate → Verify → Deliver`，
产物落在 `output/html9n-<时间戳>/`，核心文件是 **零外部依赖的 `output.html`**。

### ② 画布自由组合 → 生成 → 导出 PDF

```bash
htmlninefox workbench      # 打开画布
htmlninefox export output/html9n-2026-09-16-101500 --format pdf --paper A4
```

画布上拖入「需求 / 版式 / 内容 / 风格 / 文件 / 技能」六类节点，
点工作区的 **▶ 推进** → 自动拆解 → 组合配方 → 生成产物 →
在产物节点打开 **导出中心** 选 PDF / 逐页 PNG / 长图。

### ③ 反馈迭代 + Project Memory

```bash
# 先 dry-run 看解析结果，确认后再真实改写 output.html
htmlninefox feedback --project output/html9n-2026-09-16-101500 --note "标题大一点" --dry-run
htmlninefox feedback --project output/html9n-2026-09-16-101500 --note "颜色更稳重，参考 Vercel"
```

每次迭代写入 `revisions/revN.html`，历史可回溯。
在产物检查器点 **♡ 采用此版本并学习**，才会把品牌 / 受众 / 语气 / 禁忌 / 模板 / 主色 / 字体写进 Project Memory。
本次需求里的明确约束**永远优先于**长期记忆。

---

## 命令速查

| 命令 | 作用 |
|---|---|
| `htmlninefox expert "<prompt>"` | 一句话生成单文件 HTML（6 类型 × 11 风格预设 × 联盟路由） |
| `htmlninefox feedback --project <dir> --note "<反馈>"` | 口语反馈 → 改设计 Token → 重渲染，存 `revisions/` |
| `htmlninefox export <project>` | 导出 PDF / PNG / 长图 / PPTX / DOCX + `export-report.json` |
| `htmlninefox workbench` | 启动 Web 工作台（默认 `0.0.0.0:8620`，便于 Docker / 局域网） |
| `htmlninefox app` | 等价启动，默认 `127.0.0.1:8620`，端口占用自动顺延 |
| `htmlninefox serve` | 仅启动本地 REST API + UI 服务 |
| `htmlninefox template` | 列出 11 套审美预设（ID / 名称 / 明暗 / 来源） |
| `htmlninefox brief list \| show <id> \| add --from-md <file>` | Brief 库管理（`~/.htmlninefox/briefs/`） |
| `htmlninefox alliance list \| reload` | Skill 联盟管理 |
| `htmlninefox version` | 显示版本 |

完整参数、默认值与 `cli.py` 行号出处见 `references/cli-commands.md`。

---

## 安装与故障速查

| 现象 | 处置 |
|---|---|
| **Windows Docker 报 npipe 错误 / daemon 连不上** | Docker Desktop 的 WSL2 后端没起来。管理员 cmd 执行 `dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart` + `wsl --set-default-version 2`，**重启电脑**，再确认 `docker ps` 正常。 |
| **端口 8620 被占用** | 默认会自动顺延到 8621/8622…；需要固定失败就用 `htmlninefox app --strict-port`，或显式 `--port 9000`。 |
| **中文路径报错 / 找不到项目** | 产物目录与输出根目录避免中文与空格；`export` 的 `--output-root` 显式传 ASCII 路径（如 `D:/fox-output`）。 |
| **导出 PDF/PNG 失败** | 需要本机 Chromium 内核：Windows 复用 Edge/Chrome，Linux 装 Chromium/Chrome，或 `python -m playwright install chromium`。 |
| **没配 API Key 会怎样** | 不阻塞。自动回落离线规则引擎，产物照常生成。 |
| **想局域网 / 手机访问** | `htmlninefox serve --host 0.0.0.0 --port 8620`，用服务器 IP 打开。**尚无登录鉴权，不要直接暴露公网**，必须放在带 HTTPS 与认证的反向代理后。 |

---

## References

| 文件 | 内容 |
|---|---|
| `references/cli-commands.md` | CLI 命令全集（子命令 + 参数 + 示例 + cli.py 行号） |
| `references/canvas-workflow.md` | 无限画布创作全流程（节点类型 / 分析 / 推荐 / 组合 / 版本迭代） |
| `references/export-center.md` | 导出中心完整手册（PDF / PNG / 长图 / 兼容性报告 / 文件协议） |
| `references/project-memory.md` | v0.5 记忆系统（记住什么 / 何时写入 / 隐私边界 / 查看清空） |
| `references/pixel-garden.md` | Pixel Garden 设计系统速查（色板 / 圆角 / 投影 / 双主题 / Logo） |

---

> **GitHub**：<https://github.com/KratosLee-6/Html-ninefox>（v0.8.3 · 2026-10-25）
> **小红书搜 KratosLee 看演示**
