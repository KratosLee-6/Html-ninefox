# 📘 CLI 命令全集 · htmlninefox

> 出处：`htmlninefox/cli.py`（Click 实现，本文件所有命令与参数均逐条对照该文件行号）
> 版本：v0.5.0rc1 · 入口 `htmlninefox`（等价 `python -m htmlninefox`）

---

## 0. 顶层入口

```text
@click.group(help="Html九尾狐 · HTML 创作工作台（v{__version__}）")   # cli.py:39
@click.version_option(__version__, prog_name="htmlninefox")            # cli.py:40
def main():                                                            # cli.py:41
```

- 全局参数只有 `--version`（`cli.py:40`），打印版本后退出。
- 无子命令时 `htmlninefox` 显示子命令列表。

**子命令地图**（文件头 docstring，`cli.py:3-12`）：

| 子命令 | 作用 | 定义行 |
|---|---|---|
| `expert` | 一句话生成 HTML | `cli.py:48-87` |
| `feedback` | 反馈迭代 | `cli.py:93-115` |
| `export` | 导出 PDF / PNG | `cli.py:121-164` |
| `brief` | Brief 库管理（组） | `cli.py:170-209` |
| `template` | 列出审美模板库 | `cli.py:215-226` |
| `alliance` | Skill 联盟（组） | `cli.py:232-259` |
| `app` | 一键启动工作台 | `cli.py:265-278` |
| `workbench` | 启动 Web 工作台 | `cli.py:281-293` |
| `serve` | 仅启动 REST API + UI | `cli.py:296-303` |
| `version` | 显示版本信息 | `cli.py:309-312` |

---

## 1. `expert` — 一句话生成可发布的单文件 HTML

```text
@main.command()                                          # cli.py:48
@click.argument("prompt")                                # cli.py:49
@click.option("--skill", default=None)                   # cli.py:50
@click.option("--template", default=None)                # cli.py:51
@click.option("--type", "intent", default=None,
    type=click.Choice(["landing","dashboard","deck",
                       "poster","archdoc","doc"]))       # cli.py:52-53
@click.option("--output", "-o", default="./output")      # cli.py:54
@click.option("--quiet-llm", is_flag=True)               # cli.py:55
def expert(prompt, skill, template, intent, output, quiet_llm):   # cli.py:56
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `PROMPT` | 必填位置参数 | — | 一句话需求；空字符串直接 `sys.exit(2)`（`cli.py:59-61`） |
| `--skill` | 文本 | `None` | 指定联盟 Skill，例如 `guizang-ppt` |
| `--template` | 文本 | `None` | 风格预设 ID，取值见 `template` 子命令 |
| `--type` | 枚举 | 自动路由 | 六选一：`landing` / `dashboard` / `deck` / `poster` / `archdoc` / `doc` |
| `-o, --output` | 路径 | `./output` | 产物根目录 |
| `--quiet-llm` | 开关 | 关 | 跳过 LLM 微调，纯离线规则引擎 |

**示例**：

```bash
# 意图自动路由 + 风格自动匹配（离线可跑）
htmlninefox expert "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具"

# 强制内容类型
htmlninefox expert --type dashboard "运营数据看板，深色，展示订单和 KPI"
htmlninefox expert --type deck "发布会 PPT，主题 AI-native"
htmlninefox expert --type poster "活动宣传海报，鲜艳活力"
htmlninefox expert --type archdoc "技术方案文档，包含架构图"
htmlninefox expert --type doc "产品方案文档"

# 指定联盟 Skill / 风格预设
htmlninefox expert --skill guizang-ppt "做一个发布会 PPT"
htmlninefox expert --template fox-pixel-garden "创作工具官网"

# 纯离线（无 API Key 场景的确定性输出）
htmlninefox expert --quiet-llm "做一个开发者工具官网" -o ./output
```

**执行链路**（`pipeline.run_expert`，`cli.py:64-66`）：

```text
Analyze（需求拆解）→ Compose（组合配方）→ Generate（生成）
  → Verify（质量验证）→ Deliver（保存交付）
```

**终端输出表格**（`cli.py:69-87`）：内容类型 / 风格预设 / 联盟路由 / Brief 置信度 + 产物文件清单 + `output.html` 绝对路径。

**成功判定**：`✓ 已生成  <work>/output.html`（`cli.py:87`）。

---

## 2. `feedback` — 口语反馈 → 改设计 Token → 重渲染

```text
@main.command()                                              # cli.py:93
@click.option("--project", required=True)                    # cli.py:94
@click.option("--note", required=True)                       # cli.py:95
@click.option("--dry-run", is_flag=True)                     # cli.py:96
def feedback(project, note, dry_run):                        # cli.py:97
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--project` | ✅ | 项目目录（`expert` 的输出目录，必须含 `.foxstate.json`） |
| `--note` | ✅ | 反馈内容，口语化即可 |
| `--dry-run` | ❌ | 只解析反馈不重渲染 |

内部实现：`pipeline.run_feedback(project, note, revise=not dry_run)`（`cli.py:99`）。

**示例**：

```bash
# 先看解析结果
htmlninefox feedback --project output/html9n-2026-09-16-101500 --note "标题大一点" --dry-run

# 真实迭代
htmlninefox feedback --project output/html9n-2026-09-16-101500 --note "颜色更稳重，参考 Vercel"
htmlninefox feedback --project ./output/html9n-<时间戳> --note "换成深色主题，字号放大"
```

**dry-run 输出**（`cli.py:106-109`）：

```text
✓ 反馈解析（dry-run） <建议>
  规则: <命中的规则 ID 列表 或 —>
```

**真实迭代输出**（`cli.py:110-115`）：

```text
✓ 迭代完成  rev<N>  <项目>/revisions/rev<N>.html
  执行: <suggestion>
  规则: <rules>  模型: <model 或 rules>
  历史: <项目>/revisions
```

**失败语义**（`cli.py:100-105`）：
- 返回 `ask_user` → 黄色提示 `🦊 <追问内容>`（需求太模糊时）
- 其他失败 → 红色 `✗ <error>` 并 `sys.exit(2)`

**错误预检**：项目缺 `.foxstate.json` 时 `run_feedback` 返回
`项目缺少 .foxstate.json（请用 htmlninefox expert 生成）`（`pipeline.py:372`）。

---

## 3. `export` — PDF / PNG 导出 + 兼容性报告

```text
@main.command("export")                                            # cli.py:121
@click.argument("project")                                        # cli.py:122
@click.option("--format", type=Choice(["pdf","png"]), default="pdf")   # cli.py:123
@click.option("--scope",  type=Choice(["auto","pages","long"]), default="auto")  # cli.py:124
@click.option("--pages", default="")                              # cli.py:125
@click.option("--width",  default=1920, type=int)                 # cli.py:126
@click.option("--height", default=1080, type=int)                 # cli.py:127
@click.option("--scale",  default=2, type=click.IntRange(1,3))    # cli.py:128
@click.option("--paper",  type=Choice(["A4","Letter","A3"]), default="A4")  # cli.py:129
@click.option("--landscape", is_flag=True)                        # cli.py:130
@click.option("--output-root", default="~/htmlninefox-output")    # cli.py:131-132
def export_command(...):                                          # cli.py:133
```

| 参数 | 默认 | 有效范围 / 取值 | 说明 |
|---|---|---|---|
| `PROJECT` | 必填 | — | 项目目录（存在则直接用它）；否则按「项目名」在 `--output-root` 下查找（`cli.py:136-142`） |
| `--format` | `pdf` | `pdf` / `png` | 输出格式 |
| `--scope` | `auto` | `auto` / `pages` / `long` | `pages`=按分页结构逐页；`long`=整页长图；`auto`=自动判定 |
| `--pages` | 空=全部 | 如 `1-3,5` | 页码范围（`_parse_pages`） |
| `--width` | `1920` | 320–3840 | 画布宽 |
| `--height` | `1080` | 240–2160 | 画布高 |
| `--scale` | `2` | 1 / 2 / 3 | 图片倍率（IntRange 强校验） |
| `--paper` | `A4` | `A4` / `Letter` / `A3` | 连续页面 PDF 纸张 |
| `--landscape` | 关 | — | 连续页面 PDF 横向 |
| `--output-root` | `~/htmlninefox-output` | — | 工作台项目根目录 |

**示例**：

```bash
# 默认：A4 纵向 PDF，2x 画布 1920×1080
htmlninefox export output/html9n-2026-09-16-101500

# 逐页 PNG，明确 1-3 与第 5 页，3 倍清晰度
htmlninefox export output/html9n-2026-09-16-101500 --format png --scope pages --pages "1-3,5" --scale 3

# 完整长图（发微信 / 小红书）
htmlninefox export output/html9n-2026-09-16-101500 --format png --scope long

# 横向 A3 PDF
htmlninefox export output/html9n-2026-09-16-101500 --format pdf --paper A3 --landscape
```

**成功输出**（`cli.py:160-164`）：

```text
✓ 导出完成  PDF · 兼容性 <score> 分
  <root>/<project>/exports/<export-id>/document.pdf
  报告: <root>/<project>/exports/<export-id>/export-report.json
```

**失败输出**（`cli.py:156-159`）：

```text
✗ 导出失败：<error>
请确认已安装 Edge、Chrome，或执行 playwright install chromium。
```

---

## 4. `brief` — Brief 库管理（`~/.htmlninefox/briefs/`）

```text
@main.group()                        # cli.py:170
def brief(): ...                     # cli.py:171
brief list                           # cli.py:175-187
brief show <brief_id>               # cli.py:190-198
brief add --from-md <file>          # cli.py:201-209
```

```bash
htmlninefox brief list
htmlninefox brief show 4f2a1c9d
htmlninefox brief add --from-md ./docs/brief-saas-landing.md
```

- `list`：表格三列 ID / Goal（截断 60 字）/ 更新时间（`cli.py:181-186`）；库为空时提示 `Brief 库为空  路径: ~/.htmlninefox/briefs/`（`cli.py:178-180`）。
- `show`：直接 `print_json` 输出 `~/.htmlninefox/briefs/<id>.json` 全文（`cli.py:194-198`），文件不存在则 `sys.exit(2)`。
- `add`：`--from-md` 为**必填**（`cli.py:202`），路径先 `expanduser().resolve()`，不存在则 `exit(2)`（`cli.py:205-207`），成功打印 `✓ 已添加 Brief  <id>`。

---

## 5. `template` — 列出审美模板库

```text
@main.command("template")     # cli.py:215
def template(): ...           # cli.py:216
```

```bash
htmlninefox template
```

调用 `pipeline.list_templates()`（`cli.py:218`），输出四列表：**ID / 名称 / 明暗 / 来源**（`cli.py:219-226`）。
来源为 `builtin`（内置预设）或 `user`（`~/.htmlninefox/templates/<dir>/style.json` 用户模板，`pipeline.py:436-452`）。

**11 套内置预设 ID**（`generators/_tokens.py`）：

| ID | 名称 | 明暗 |
|---|---|---|
| `linear-light` | Linear 浅色 · 克制工程师风 | 浅色（**默认预设**） |
| `vercel-dark` | Vercel 深色 · 极客暗夜 | 深色 |
| `guizang-magazine` | 归藏电子杂志 · 衬线编辑风 | 浅色 |
| `shadcn-dashboard` | shadcn 看板 · 中性数据风 | 深色 |
| `vibrant-poster` | 高活力海报 · 大字报风 | 深色 |
| `doc-clean` | Stripe 文档 · 专业清爽 | 浅色 |
| `fox-pixel-garden` | 九尾狐像素花园 · 深蓝与薄荷 | 浅色 |
| `fox-duotone-studio` | 九尾狐双色工作室 · 暖白与电光蓝 | 浅色 |
| `fox-editorial-ink` | 九尾狐编辑墨水 · 纸感叙事 | 浅色 |
| `fox-swiss-signal` | 九尾狐瑞士信号 · 灰白与安全橙 | 浅色 |
| `fox-soft-silver` | 九尾狐柔银界面 · 奶油灰与薄荷 | 浅色 |

---

## 6. `alliance` — Skill 联盟管理

```text
@main.group()                  # cli.py:232
def alliance(): ...            # cli.py:233
alliance list                  # cli.py:237-252
alliance reload                # cli.py:255-259
```

```bash
htmlninefox alliance list
htmlninefox alliance reload
```

- `list`：五列 Skill / 作者 / 接管内容 / 状态 / 来源（`cli.py:241-250`）。
  状态为 `已安装` 或 `未安装→本地兜底`（`cli.py:248`）。
  末尾提示：`加入联盟：把 skill-manifest.yaml 放到 ~/.htmlninefox/alliance/`（`cli.py:252`）。
- `reload`：热重载 manifest，打印 `✓ 已重载  <N> 个联盟 skill`（`cli.py:259`）。

---

## 7. 启动类命令（`app` / `workbench` / `serve`）

### 7.1 `app` — 一键启动（适合 wheel / uv / pipx / 桌面包）

```text
@main.command("app")                                     # cli.py:265
@click.option("--host", default="127.0.0.1")             # cli.py:266
@click.option("--port", default=8620)                    # cli.py:267
@click.option("--output", "-o", default=None)            # cli.py:268
@click.option("--open-browser/--no-open-browser", default=True)  # cli.py:269
@click.option("--strict-port", is_flag=True)             # cli.py:270
```

`--strict-port` 关闭端口顺延（`fallback_port=not strict_port`，`cli.py:277`）。

### 7.2 `workbench` — Web 工作台（推荐入口）

```text
@main.command()                                          # cli.py:281
@click.option("--host", default="0.0.0.0")               # cli.py:282
@click.option("--port", default=8620)                    # cli.py:283
@click.option("--output", "-o", default=None)            # cli.py:284
@click.option("--open-browser/--no-open-browser", default=True)  # cli.py:285
```

**默认监听 `0.0.0.0`**，方便 Docker / 局域网；端口占用始终自动顺延（`cli.py:292`）。

### 7.3 `serve` — 仅启动 REST API + UI

```text
@main.command()                                          # cli.py:296
@click.option("--host", default="127.0.0.1")             # cli.py:297
@click.option("--port", default=8620)                    # cli.py:298
@click.option("--output", "-o", default=None)            # cli.py:299
```

**无端口顺延、无浏览器自动打开**（直接 `app.serve(host, port, output)`，`cli.py:303`）。

**示例**：

```bash
htmlninefox workbench                                  # 本机默认
htmlninefox workbench --port 9000 -o ./output           # 换端口 + 自定义产物目录
htmlninefox app --no-open-browser                       # 服务器 / CI
htmlninefox app --strict-port                           # 端口被占用直接失败
htmlninefox serve --host 0.0.0.0 --port 8620            # 局域网共享
```

**启动行为**（`launcher.launch_workspace`）：
1. `find_available_port(host, port)` — 首选端口起连续探测最多 20 个（`launcher.py:17-29`）。
2. 就绪判定走 `GET /api/health`，就绪后**只打开一次**浏览器（`launcher.py:32-46`）。
3. 全部不可用时报错：`<host>:<port> 起连续 <20> 个端口均不可用`（`launcher.py:28`）。

---

## 8. `version` — 版本信息

```text
@main.command("version")     # cli.py:309
def version(): ...           # cli.py:310
```

```bash
htmlninefox version
# 🦊 Html九尾狐 v0.5.0rc1 · MIT License
```

---

## 9. 产物目录结构（Agent 需要知道的落点）

`expert` 每次生成创建 **`<output>/html9n-<YYYY-MM-DD-HHMMSS>/`**（`pipeline.py:128-136`），
同秒冲突时追加 `-2`、`-3` 后缀（`pipeline.py:132-135`）。

```text
output/html9n-2026-09-16-101500/
├── output.html          # ✅ 核心交付物：单文件、零外部依赖
├── brief.json           # Brief 结构化结果
├── brief.md             # Brief 可读版
├── style.md             # 风格 Token 表
├── assets.json          # 区块规划
├── .foxstate.json       # 迭代状态（模板 / 区块 / 附件 / Skill / 选择模式）
├── recipe-run.json      # Analyze→Compose→Generate→Verify→Deliver 运行证据
├── revisions/           # rev1.html / rev2.html … 反馈迭代历史
│   └── revN.html
├── feedback.md          # 反馈沉淀
└── exports/             # export 子命令产物（不覆盖 output.html）
    └── <export-id>/
        ├── document.pdf  或  page-01.png …
        └── export-report.json
```

**六类生成内容**（`--type` 取值 → 中文）：

| 值 | 中文 | 典型区块序列 |
|---|---|---|
| `landing` | 落地页 | nav → hero → features → showcase → pricing → faq → cta_footer |
| `dashboard` | 数据看板 | topbar → kpi_row → charts → table → activity |
| `deck` | 发布会 PPT | cover → problem → solution → demo → metrics → roadmap → ending |
| `poster` | 海报 | headline → key_info → details → action_bar |
| `archdoc` | 架构文档 | title → layer_diagram → flow → component_table → decisions |
| `doc` | 文档 | title → summary → sections → key_points → table → conclusion |

---

> **GitHub**：<https://github.com/KratosLee-6/Html-ninefox>
> **小红书搜 KratosLee 看演示**
