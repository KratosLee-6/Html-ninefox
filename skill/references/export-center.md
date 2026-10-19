# 📤 导出中心（Export Center）完整手册

> 出处：`docs/EXPORT-CENTER.md`、`htmlninefox/exporting.py`、`htmlninefox/cli.py:121-164`、`server/app.py`
> 状态：**v0.4.2 已实现 PDF / PNG**；PPTX 高保真 → v0.5「可汇报」；可编辑 PPTX / 语义 DOCX → v0.6

---

## 1. 一句话原则

> **HTML 是唯一源文件，PDF / 图片 / 未来 PPTX / DOCX 都是面向不同交付场景的派生格式。**

因此：

- 导出**永远不覆盖 `output.html`**，每次写入独立的 `exports/<export-id>/` 目录。
- 「视觉高保真」和「Office 可编辑」是**两条路线**，不假装可以无损互通。
- 无法映射的动态内容（动画 / 音视频 / WebGL）**冻结为静态画面**，并在报告里写明。

---

## 2. 流水线：Analyze → Route → Render → Verify → Deliver

```text
Artifact HTML + artifact.json
          ↓
    ExportAnalyzer            ← 预检：分页结构 / 网络资源 / 动态内容 / 体积
          ↓
      ExportPlan              ← 格式 / 页面范围 / 清晰度 / 纸张 / 降级项
  ┌───────┼────────┬──────────┐
 PDF    Image     PPTX       DOCX
Chromium 截图   fidelity   semantic
                          （后续版本）
          ↓
 export-report.json + files
```

**全部在本地完成，不上传用户 HTML、文件或 API Key。**

---

## 3. 预检（`analyze_project`）会告诉你什么

对项目 HTML 做一次静态分析（`exporting.py:91-141`），返回：

| 字段 | 含义 |
|---|---|
| `title` | HTML `<title>` 或项目名 |
| `intent` | 内容类型（`landing` / `dashboard` / `deck` / `poster` / `archdoc` / `doc`） |
| `preset_id` | 使用的风格预设 |
| `source_file` / `source_size` | 源 HTML 文件名与字节数 |
| `page_model` | `{ selector, count, paginated }` — 分页选择器、页数、是否分页结构 |
| `viewport` | 按 intent 推断的默认画布尺寸 |
| `features` | 检测到的动态特征（`animation` / `video` / `audio` / `webgl` / `filter`） |
| `external_assets` | 网络资源数量 |
| `compatibility_score` | 兼容性评分（见下） |
| `warnings` | 告警清单（code / level / message） |
| `recommended` | 推荐的格式与范围 |
| `runtime` | 本机浏览器与 Playwright 能力 |

### 3.1 默认画布尺寸（`_default_viewport`，`exporting.py:530-536`）

| intent | 尺寸 |
|---|---|
| `poster` | `1080 × 1440`（竖版） |
| `deck` | `1920 × 1080`（横版 16:9） |
| 其他（landing / dashboard / doc / archdoc） | `1440 × 900` |

### 3.2 兼容性评分算法（`exporting.py:119`）

```text
score = max(45, 100 - Σ penalty)
penalty：level == "error" → 20 分；其他 level → 8 分
```

所以最低不会低于 **45 分**。

### 3.3 五类告警码

| code | level | 触发条件 | 含义 |
|---|---|---|---|
| `external_assets` | warning | 存在网络资源 | 离线导出时可能缺图或字体 |
| `dynamic_content_flattened` | info | 出现 `video` / `audio` / `webgl` / `animation` | 导出时会冻结为静态画面 |
| `page_limit` | **error** | 页数 > **200** | 单次最多导出 200 页 |
| `network_idle_timeout` | info | 渲染时网络一直不空闲 | 已按当前稳定画面导出 |
| `page_model_missing` | info | 未检测到分页结构 | 自动改为整页长图或自然分页 |

> ⚠️ **出现 `level == "error"` 的告警时导出会被直接拦住**（`exporting.py:178-180`），
> 必须先用 `--pages` 缩范围或换 `--scope long`。

### 3.4 推荐默认值（`exporting.py:135-138`）

| 条件 | 推荐格式 | 推荐范围 |
|---|---|---|
| `intent` ∈ {`doc`, `archdoc`, `landing`} | `pdf` | 有分页选择器 → `pages`，否则 `long` |
| 其他 intent | `png` | 同上 |

产品层面的推荐（`docs/EXPORT-CENTER.md`）：

- Landing / Dashboard / Poster → **PDF + PNG**
- Deck → **PPTX 高保真版 + PDF**（v0.5 落地）
- Doc / Archdoc → **PDF + DOCX 语义版**（v0.6 落地）

---

## 4. 三个导出范围（`--scope`）

| scope | 行为 | 适用 |
|---|---|---|
| `auto` | 按预检结果自动判定（有分页选择器 → `pages`，否则 `long`） | 默认 |
| `pages` | 按分页结构**逐页**输出 | Deck、海报系列、逐页汇报 |
| `long` | **整页长图** / 连续自然分页 | 落地页、文档、要发微信/小红书的长图 |

**分页页数上限 200**（`_PAGE_LIMIT`，`exporting.py:23`）。
`--pages` 超过 200 页时报 `export_page_limit`（HTTP 413）。

---

## 5. CLI 用法

```text
htmlninefox export PROJECT
    [--format {pdf,png}]        # 默认 pdf
    [--scope {auto,pages,long}] # 默认 auto
    [--pages "1-3,5"]           # 留空 = 全部
    [--width 1920]              # 320–3840
    [--height 1080]             # 240–2160
    [--scale {1,2,3}]           # 默认 2
    [--paper {A4,Letter,A3}]    # 默认 A4
    [--landscape]               # 连续页面 PDF 横向
    [--output-root ~/htmlninefox-output]
```

`PROJECT` 两种写法（`cli.py:136-142`）：

1. **直接给项目目录** → 用它，根目录取它的父目录。
2. **只给项目名** → 在 `--output-root` 下查找。

**典型调用**：

```bash
# 落地页 → A4 纵向 PDF
htmlninefox export output/html9n-2026-09-16-101500

# 发布会 PPT → 逐页 PNG，3 倍清晰度，只导 1-3 与第 5 页
htmlninefox export output/html9n-2026-09-16-101500 \
  --format png --scope pages --pages "1-3,5" --scale 3

# 长图（微信 / 小红书）→ 整页 PNG
htmlninefox export output/html9n-2026-09-16-101500 --format png --scope long

# 横向 A3 海报 PDF
htmlninefox export output/html9n-2026-09-16-101500 --format pdf --paper A3 --landscape

# 海报按原生竖版画布导出
htmlninefox export output/html9n-2026-09-16-101500 --width 1080 --height 1440 --scale 2
```

**成功输出**：

```text
✓ 导出完成  PDF · 兼容性 92 分
  <root>/<project>/exports/20260916-101500-a1b2c3/document.pdf
  报告: <root>/<project>/exports/20260916-101500-a1b2c3/export-report.json
```

---

## 6. 工作台里的导出中心

产物节点的「导出」按钮打开弹窗（`docs/EXPORT-CENTER.md` §7）：

1. 选 **PDF / 图片**（v0.4.2 可用；PPTX / DOCX 待后续版本）。
2. 选 **全部页面**或**页面范围**。
3. 设置**画布尺寸 / 宽高比 / 图片倍率 / 是否嵌入字体**。
4. **导出前**显示兼容性评分与可能降级项。
5. **导出后**提供文件、报告和「重新导出」入口。

**后端接口**：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/exports/capabilities` | 可用格式 / 纸张 / 倍率 / 本机浏览器 |
| POST | `/api/exports/analyze` | 预检，返回上表字段 |
| POST | `/api/exports` | 执行导出（异步 job + 下载 URL） |
| GET | `/api/jobs/<id>` | 轮询进度 |
| DELETE | `/api/jobs/<id>` | 取消任务 |

任务态：**可重试、可取消、有明确错误、有兼容性报告**（不损害源 HTML、不覆盖已有产物）。

---

## 7. 参数字段与校验规则

`normalize_export_request`（`exporting.py:144-172`）：

| 字段 | 默认 | 合法域 | 越界错误码 |
|---|---|---|---|
| `project_name` | 必填 | 非空 | `export_project_required` (400) |
| `format` | `pdf` | `pdf` / `png` | `export_format_unsupported` (400) |
| `scope` | `auto` | `auto` / `pages` / `long` | `export_scope_invalid` (400) |
| `width` | `1920` | 320 – 3840 | 自动夹取到边界 |
| `height` | `1080` | 240 – 2160 | 自动夹取到边界 |
| `scale` | `2` | 1 – 3 | 自动夹取到边界 |
| `paper` | `A4` | `A4` / `Letter` / `A3` | `export_paper_invalid` (400) |
| `pages` | 空（全部） | 如 `1-3,5` | 超 200 页 → `export_page_limit` (413) |
| `landscape` | `false` | 布尔 | — |

CLI 侧的 `--scale` 用 `click.IntRange(1, 3)` 在参数层就拦住非法值（`cli.py:128`）。

---

## 8. 渲染细节（Agent 排错时要知道）

### 8.1 静态化处理

渲染前注入 `_FREEZE_CSS`（`exporting.py:24-34`）：

```css
* { animation-duration: 0s !important; transition-duration: 0s !important;
    animation-iteration-count: 1 !important; caret-color: transparent !important; }
[data-export-hide], .fox-export-hide { display: none !important; }
```

→ 动画 / 过渡被冻结在首帧；带 `data-export-hide` 或 `.fox-export-hide` 的元素**不进导出**（做导出专用的隐藏标记）。

截图统一带 `animations="disabled"`。

### 8.2 PNG

| scope | 产物文件名 |
|---|---|
| `pages` | `page-01.png` / `page-02.png` …（两位补零，按页码） |
| `long` | `full-page.png`（`full_page=True`） |

逐页导出时会先 `_activate_page(selector, index)` 激活目标页再截图，保证拿到的是**那一页**而不是首屏。

### 8.3 PDF 两条路

**`scope=pages` 且有分页选择器（Deck 类）**：

- `emulate_media("print")`。
- 用 JS 给非选中页打上 `data-fox-export-skip` 并隐藏，选中页加 `on` 类。
- 注入 `@page { size: <width>px <height>px; margin: 0 }`，
  逐个分页元素设为 `break-after: page`（每页一张）。
- 隐藏 `.hud`、`.deck > .nav`、`.counter` 等交互控件。
- `page.pdf(print_background=True, prefer_css_page_size=True, margin: 0)`。

**`scope ≠ pages`（连续页面）**：

- `page.pdf(format=<paper>, landscape=<bool>, print_background=True, margin: 0.35in)`。
- 依赖浏览器自然分页；`A4` / `Letter` / `A3` 由 `--paper` 决定。

### 8.4 浏览器选择（`_browser_candidates`，`exporting.py:403-443`）

优先 Playwright 自带 Chromium，随后依次尝试：

| 环境 | 用的内核 |
|---|---|
| Windows 安装包 / 普通用户 | 系统 **Microsoft Edge**，其次 Chrome |
| Linux | **Chromium** 或 **Chrome** |
| Docker | 镜像**内置 Chromium**（`HTMLNINEFOX_BROWSER_PATH=/usr/bin/chromium`） |
| Python / uv | 可 `python -m playwright install chromium` 装隔离浏览器 |

缺少浏览器时的报错（`cli.py:158`）：

```text
请确认已安装 Edge、Chrome，或执行 playwright install chromium。
```

---

## 9. 文件协议

```text
project/
├── output.html                    # 源文件永不被覆盖
├── .foxstate.json
└── exports/
    └── <YYYYMMDD-HHMMSS-短哈希>/    # 例如 20260916-101500-a1b2c3
        ├── document.pdf            或
        ├── page-01.png … page-NN.png
        ├── full-page.png
        └── export-report.json
```

`export-report.json` 记录（`exporting.py:207-232`）：

- 源项目与源文件
- **请求参数**（format / scope / pages / width / height / scale / paper / landscape）
- **分页选择器**与页数
- **浏览器版本**（`browser_info`）
- **文件清单**（名称 / 大小 / 下载 URL）
- **网络资源**检测结果
- **静态化与降级告警**（`warnings`，含渲染期新增的 `network_idle_timeout` / `page_model_missing`）
- `compatibility_score`

用途：**复现问题、诊断导出差异、审计降级项**。

---

## 10. 验收标准与边界

官方验收标准（`docs/EXPORT-CENTER.md` §9）：

- PDF / 图片与 HTML 截图**关键区域视觉差异可控**。
- 导出失败**不会损坏原始 HTML、不会覆盖已有产物**。
- 每次导出**可重试、可取消**，有明确错误和兼容性报告。
- 未来 PPTX 高保真模式不出现**裁切、错页、字体漂移导致的布局破坏**。
- DOCX 只承诺**语义正确**，不虚假承诺自由布局像素级一致。

**明确不做的事**：

- 不把 Word 当作落地页 / 数据看板 / 自由画布作品的通用导出目标 —— 这些默认出 PDF 或图片。
- 不在一个「万能转换器」里猜格式 —— PDF / 逐页 PNG / 长图 PNG / 高保真 PPTX / 可编辑 PPTX / DOCX 是**不同 profile**，先路由再执行。

---

## 11. 排错清单

| 现象 | 原因 | 处置 |
|---|---|---|
| `✗ 导出失败：...请确认已安装 Edge、Chrome...` | 本机无可用 Chromium 内核 | 装 Edge/Chrome，或 `python -m playwright install chromium` |
| 导出被拦住，报告里是 `page_limit` (error) | 页数 > 200 | 用 `--pages` 缩范围或 `--scope long` |
| 图片里缺图 / 字体变了 | `external_assets` warning | 把素材内联，或联网后重导 |
| 动画 / 视频位置是静态画面 | `dynamic_content_flattened` (info) | 预期行为，报告已记录 |
| 长图被截断或分页错乱 | `page_model_missing` (info) → 已自动转 `long` | 显式指定 `--scope long` 或 `--scope pages` |
| Deck 导出的 PDF 每页错位 | 分页选择器不匹配 | 检查 HTML 里的 `data-page` / `.page` / `.slide` 结构 |
| 不想让某个控件出现在导出里 | — | 给元素加 `data-export-hide` 或 `class="fox-export-hide"` |
| 导出慢 / 一直转 | 页面持续网络请求 | 报告里会有 `network_idle_timeout`，已按当前稳定画面导出 |
| 要 Word / PPT 可编辑文件 | v0.5 尚未提供 | 现在出 PDF / PNG；等 v0.5 PPTX 高保真、v0.6 可编辑 |

---

> **GitHub**：<https://github.com/KratosLee-6/Html-ninefox>
> **小红书搜 KratosLee 看演示**
