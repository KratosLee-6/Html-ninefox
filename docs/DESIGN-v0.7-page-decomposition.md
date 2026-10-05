# v0.7 设计：网页反向拆解

状态：**设计稿，不含实现**。目的是在动手前把「页面分块怎么变成可编辑的东西」
这件事的形状定下来，因为重新核实后发现它比原路线图写的大得多。

## 先更正一件必须先说的事

`docs/ROADMAP-v0.6.1-v0.7.md` 曾写「`intake.py` 已具备约 80% 所需能力」，并给了一张
带行号的表。**那张表的每个行号都指向本仓库中不存在的版本**——既不匹配当前
`intake.py`，也不匹配 `.codex_tmp/committed/` 快照。80% 这个数字没有可核验出处。
ROADMAP 已按真实情况重写。

重新核实后的结论分成两半：

| 那一半 | 现状 |
|---|---|
| **抓取** | 接近完整。SSRF 逐跳校验、连接级 IP 绑定（`_PinnedHTTPSHandler` `intake.py:236`）、大小/类型/频率限制、原始整页落盘并可回读（`save_evidence` `intake.py:484`、`CandidateStore.body` `intake.py:705`） |
| **拆解** | **基本不存在。** 产物是 `skeleton{headings, semantic:{tag:次数}, links:数字, images:数字}`——扁平计数器，不是结构树。没有正文抽取、没有 DOM 树、没有列表/表格、依赖里**连 HTML 解析库都没有**（`pyproject.toml:13-18` 只有 pyyaml/click/rich/playwright） |
| **生成侧消费** | `blocks` 是每 intent 的**固定 id 词表**（`rules.py:135-142`），6 个渲染器做 34 处 `if "pricing" in blocks` 分支，**正文全是硬编码** |

**但有一条被忽略的现成能力**：`server/app.py:248-251` **今天就已经把整页原样 HTML 导入
素材库**（`_api_intake_decide` → `import_files`）。也就是说「整页当模板收进来」现在
就能做，缺的只是「拆成结构」。而且版权闸门已经存在：`inspiration-only` 的候选在
`app.py:240-242` 被拒绝进模板库。

## 三段链条，只缺中间那一段

```
URL ──fetch──> 原始整页 HTML                ✅ 已有，且防护是真的
      ↓
   decompose    ← ❌ 缺：页面 → 结构化分块
      ↓
   可编辑项目                                ⚠️ 部分已有（见下）
      ↓
   generate    ← ⚠️ 存在但不消费外部结构
```

## 好消息：可编辑项目这一段**已经有了承载体**

`.foxstate.json`（`pipeline.py:274-291`）当前写入：

| 字段 | 内容 |
|---|---|
| `brief` | 拆解后的结构化 brief |
| `assets` | 含 `blocks`、`block_notes`、`composition` |
| `composition` | 用户选中的分区（`blocks`、`selection_mode`） |
| `preset` | 令牌（去掉 `_` 前缀的内部字段） |

同一目录还落 `assets.json`、`style.md`、`output.html`（`pipeline.py:270-272`）。

**所以页面分块不需要新文件、新概念、新存储格式。** 它可以顺着 `composition` /
`assets.blocks` 进去。唯一的闸门在 `pipeline.py:224-228`：

```python
selected_blocks = [
    str(block).strip() for block in composition.get("blocks", []) if str(block).strip()
]
```

这一行**把一切都压成了字符串**。`blocks` 今天是 `list[str]`，所以下游
`blocks_of` (`generators/_shared.py:132`) 只能读出 id 列表，生成器于是只能
`if "pricing" in blocks` 去选**硬编码的**内容。

**这一行是整件事的瓶颈，而且是唯一的一行。**

## 设计：让 `blocks` 从 id 列表变成带内容的分块描述

### 形状

`blocks` 的元素从 `str` 变成 `dict`，两种形态并存：

```jsonc
// 现状：固定词表里的 id，生成器走硬编码分支
"pricing"

// v0.7：从页面拆出来的分块，自带内容与出处
{
  "id": "section-7",
  "kind": "features",              // 对齐既有词表，让生成器知道怎么排版
  "heading": "为什么选我们",
  "content": "...",                // provenance 决定它能不能是原文
  "provenance": "verbatim" | "paraphrased" | "structure_only",
  "source_url": "https://...",
  "ordinal": 7
}
```

`kind` 对齐 `_INTENT_BLOCKS` 的词表，是关键设计：它让排版决策继续复用现有的
per-intent 词汇，而内容来自页面。**结构借现有体系，内容才是新的。**

### 三处改动，只有第三处是真工作

| # | 改动 | 落点 | 量级 |
|---|---|---|---|
| 1 | `blocks` 允许 dict 通过 | `pipeline.py:224-228` 一处 | 几行 |
| 2 | 旁挂一个结构化读取器 + 替换 34 处 `in blocks` | `generators/_shared.py` + 6 个渲染器 | 机械 |
| 3 | **页面分块抽取器** + **一个渲染器**学会渲染真实分块 | 新文件 + 一个渲染器 | **这才是新建** |

第 2 步的 34 处分布：`landing.py:7` `deck.py:7` `doc.py:6` `dashboard.py:5`
`archdoc.py:5` `poster.py:4`。全是同一种形状的替换。

**为什么不改 `blocks_of` 本身**：它的语义是「返回 id 列表」，6 个渲染器的成员判断全靠它。
新通道应当**旁挂**一个读取器，两者并存。

### 第一个目标选 `doc`，**不是** `landing`

初稿我选 `landing`（它最像一个网页），**这是错的**，理由是硬证据：

`experts/generate_expert.py:99` 的分叉是
`if tmpl_path.exists() and jinja2 is not None:`，命中即在 `:113` **直接 return**，
原生渲染器在 `:127`，排在其后。而 `htmlninefox/templates/landing.html` **存在**（182 行）。

我逐行核过该模板：它只引用 `brief.brief.content.headline` 与
`style.tokens.brand_name`，**完全没有引用 `assets` 或 `blocks`**。

所以——**一旦部署环境装了 jinja2（它在 `templates` extra 里），landing 的原生渲染器
永远不会被调用，我为它加的分块通道是死代码。**

`templates/` 下只有 4 个模板：`landing.html`、`baoyu-slide-deck.html`、
`beautiful-html-templates.html`、`frontend-slides.html`。因此安全的第一目标是
**没有模板文件**的 intent：`dashboard` / `poster` / `archdoc` / `doc`
（`deck` 也在 `_INTENT_TEMPLATE_ALIAS_NO_FALLBACK` 里，安全）。

这四个里选 **`doc`**：它的词表 `["title","summary","sections","key_points",
"table","conclusion"]`（`rules.py:141`）本身就是一个通用网页大纲。

**未确认**：本机 `.venv` 与默认 `python` 都没有 jinja2，所以当前实际走的是原生路径；
但打包环境（`packaging/windows/build_portable.py` 等）是否会装 jinja2 **未确认**。
这个不确定性本身就是「别拿 landing 开刀」的理由。

## 三条会让实现悄悄失效的约束

### 一、重渲染是「从状态重算」，不是增量修改

`pipeline.py:471-475` 的 `_render_state` 只用 `state["intent"]` / `state["brief"]` /
preset / `state["assets"]` **重新调渲染器**。任何不在这四个字段里的信息，
在下一次 `run_feedback` / `rerun_project` 时会**全部丢失**。

**所以页面分块必须落进 `state["assets"]`**（`pipeline.py:282` 整对象落盘，天然满足），
而不是只活在渲染器内存里。这条是本设计里最硬的约束。

### 二、没有版本迁移，所以新读取器必须同时吃两种形态

`.foxstate.json` 的 `version: "v0.3"`（`pipeline.py:275`）**没有任何读侧**——
`revisions.py:101-109` 的 `load_state` 除 `revision` 外不做任何 schema 校验，
多写少写都不报错，只在消费处 `.get(key, default)` 静默降级。**没有版本协商机制。**

而 `blocks` 今天已经在磁盘上是 `list[str]`（用户选分区就是选 id）。
所以新的读取器**必须同时接受 `str` 与 `dict`**，否则用户手上已有的项目会静默变空。
这不是「以后再兼容」，是**第一版就必须**。

### 三、`blocks` 通道今天只能「勾选写死的 section」

现有语义的边界值得写清楚，因为它正是 v0.7 要替换的东西：

```
用户从私人模板选 5 个 block
  → 得到的不是那 5 个 block 的内容
  → 而是九尾狐自己写死的那 5 个 section
```

`user_gallery.py:235` 的 `_block_id()` 就是这个妥协的体现——用关键词把真实页面名
**映射**到九尾狐的 id 上，**真实 HTML 内容在此处被丢弃**。

v0.7 的实质就是让这条通道**能携带内容**，而不是只携带选择。

## 顺带查出的两个既存问题（不属于 v0.7，但该记下来）

### 一、`_INTENT_BLOCKS` 有**三份**副本，且没有任何机制保证同步

| 副本 | 位置 | 状态 |
|---|---|---|
| `_INTENT_BLOCKS` | `rules.py:135-142` | 权威 |
| `_PREVIEW_BLOCKS` | `pipeline.py:50-57` | 逐字相同，**无 import 关系**，仅用于 `pipeline.py:523` 预览 |
| `BLOCKS_BY_INTENT` | `user_gallery.py:28-33` | **不完整**，缺 `poster` 与 `archdoc` |

`tests/` 里唯一的断言是 `test_rules.py:58-60` 的 `rules` 对**自己**的自洽检查，
**没有任何跨副本测试**。

**不同步的后果是静默的**：所有渲染器都是 `if "nav" in blocks:` 这种成员判断，
传入一个不认识的 id → **该 section 静默消失，没有 warning**。而
`blocks_of(assets) or [硬编码全量默认]`（`landing.py:118`）的兜底会把错误**掩盖**得更深。

**未确认**：没有实际构造失配词表跑一次渲染来观察产物（需要写文件，超出只读边界）。
但「三份、无守卫、失配静默」这三点是确认的。

### 二、`dashboard.py` 的 docstring 与代码不符

`dashboard.py:4` 声称「数据来自 `assets['chart_data']` 或默认样例」，但 `render`
（`:99-155`）**从未引用 `chart_data`**，柱状图是写死的
`bars = [42, 58, 47, 71, 66, 88, 79]`（`dashboard.py:125`）。

`assets` 里的 `chart_data` 字段确实存在（`asset_expert.py:70`），但**没有渲染器消费它**。
**不要把它当成已有的内容通道。**

### 抽取器放哪：复用 `components` 的实现，不新写一套

`intake.py:730-748` 的 `extract_components` 已经是「逐语义块切分」的实现，
`SECTION_TAGS`（`intake.py:557`）已经有区块标签表。v0.7 的抽取器应当是
**把它的 `kind == "components"` 门禁（`intake.py:789-790`）拿掉、放开 12 个上限
（`intake.py:746`）、补全块内结构**，而不是另起炉灶。

同理，`user_gallery.py:119-135` 已经在用 `DATA_PAGE_RE` / `PAGE_CLASS_RE` 切「页」——
**两套抽取器职责重叠且互不调用**，这是既存重复。v0.7 不应该再加第三套；
设计要明确它们未来的关系（合并 or 明确分工），但**合并是独立的一笔，不塞进 v0.7**。

## 版权：现有的规则是二元的，而 v0.7 需要按字段

现状：`app.py:240-242` 只区分「`inspiration-only` 不许进模板库」与「其余可以」。

v0.7 更细：几乎任何页面都可以合法地学**结构、排版、配色、字体层级**，
但**正文与图片**不能照抄。所以模型里每个字段要带 `provenance`：

| provenance | 含义 | 允许进入产物 |
|---|---|---|
| `structure_only` | 只有结构与层级，无原文 | ✅ |
| `paraphrased` | 改写过的文本 | ✅ |
| `verbatim` | 原文照搬 | **仅当 `license_class == "open"`** |

这条规则应该落在**生成前的那一步**（渲染器拿到分块时），而不是抓取时——
因为 `inspiration-only` 的页面拆出来的结构仍然完全可用，拦掉正文不拦结构。
这和现有规则的差别是：现在是整页进或不进，将来是**字段级**。

**未确认**：`LICENSE_CLASSES` 的三档具体语义（`intake.py:40`）需要读原文，
以及「改写」由谁做（离线规则引擎还是 LLM）会直接决定 `paraphrased` 能不能自动产生。

## 交付判据（照本仓库一贯的形状）

不是「做完了」，是「能证明」：

- **兼容**：新读取器在 `blocks` 为 `["pricing","faq"]`（旧形态）与
  `[{"id":"pricing",...}]`（新形态）下**都返回正确结果**。没有版本迁移兜底，
  旧项目静默变空是不可接受的失败模式
- **抽取器**：给一份真实页面的 fixture，断言拆出的分块**结构正确**（标题层级、
  区块边界、顺序），且每块都带 `provenance`
- **版权**：`verbatim` 内容在 `inspiration-only` 页面上的渲染结果里**不出现**——
  变异验证：去掉这道过滤，门禁必须变红
- **消费**：`doc.py` 在传入 dict 形态 `blocks` 时渲染出对应分块；
  变异：让它退回 `in blocks` 字符串判断，门禁必须变红
- **重渲染不丢**：跑一次 `run_feedback` / `rerun_project`，分块仍在产物里。
  变异：把分块从 `state["assets"]` 里挪走，门禁必须变红
- **既有行为不变**：6 个渲染器的 34 处分支在改动后**行为不变**（快照对比）
- 全量回归 + `e2e_verify.py` 22/22 不退化

## 「桥」查清了：样式那一半有，内容那一半没有

这一条原本是「未确认」，现已查实（`server/app.py` 的 intake 路由逐条读过）：

一个候选的出口只有五条——
`approve`（整页 HTML 进素材库）、`components/import`、`motion/import`、
`style-presets/create`、`analyze`。**没有一条通向 `composition`、`assets`
或生成链路。**

但其中两条是真桥：

### 样式：桥已存在，缺的是「角色归因」

`intake.py:1047-1067` 的 `build_style_preset(candidate)` 把候选的 tokens 变成
一个用户风格预设，`app.py:305` 落盘，`pipeline.py:278` 作为 `preset_id` 进生成。
**这条路今天就能走通。**

它粗在两处（`intake.py:1052-1054`）：

```python
primary = _hex_solid(colors[0]) if colors else "#173C8F"
accent  = _hex_solid(colors[1]) if len(colors) > 1 else "#49B894"
font_stack = fonts[0] if fonts else "Inter"     # heading 与 body 用同一个
```

**「第 1 个颜色是主色、第 2 个是强调、字体不分 heading/body」**——
这正是缺口表里「配色需角色归因」与「字体需区分 display/body」两条的所在地。
**修的位置是 `build_style_preset` 本身，不是新建。**

### 内容：没有桥，这是 v0.7 真正的新建部分

`extract_components`（`intake.py:730-748`）**已经**产出结构化 section 切片
`{tag, class, text_head, snippet}`（`intake.py:740-745`），落进候选目录与组件库
（`intake.py:675-680`、`intake.py:783`）。**但它到不了生成链路。**

所以 v0.7 的形状现在很明确：

| 半边 | 桥 | 要做的 |
|---|---|---|
| 配色 / 字体 | ✅ 已有（`build_style_preset` → `preset_id`） | 在 `intake.py:1047-1067` 加角色归因 |
| **分块 / 内容** | ❌ 没有 | **新建**：从候选的 section 切片 → `composition`/`assets` → 一个渲染器 |

## 明确不在 v0.7 范围内

- **跟随外部样式表**（`<link rel="stylesheet">`）。抓 CSS 会显著放大 SSRF 暴露面，
  必须在同一个 PR 里单独设计，不能顺手加。
- **图片抽取**。除了版权，还有远程资源可达性、尺寸、占位图的问题。
- **完整还原栅格/断点/盒模型**。这是「像素级还原」，与「结构可编辑」是两个产品。
- **合并 `intake.py` 与 `user_gallery.py` 两套抽取器**。是独立的一笔。

## 未确认

- **`intake.py` 的 section 切片有没有接到生成链路的桥？** —— **已查实：没有。**
  `server/app.py` 的 intake 路由逐条读过，候选的出口只有 approve / components /
  motion / style-presets / analyze，**没有一条通向 `composition` 或 `assets`**。
  唯一通向生成的是 `build_style_preset` 那条（见正文「桥查清了」一节），它只带走
  颜色与字体，不带内容。
- `LICENSE_CLASSES` 三档的确切语义（`intake.py:40`）
- 部署环境是否安装 jinja2。本机 `.venv` 与默认 `python` 都没有，但打包环境未确认。
  这个不确定性本身就是「别拿 landing 开刀」的理由。
- 画布 `nodes` 的完整 kind 取值：只确认了 `'ws'`（`canvas-engine.js:100`），
  其余未确认；而 `storage.py:268-272` **原样透传不逐字段校验**
- `templates/` 下另三个模板（`beautiful-html-templates.html`、
  `baoyu-slide-deck.html`、`frontend-slides.html`）的实际内容与是否消费 `assets`
  **未逐一核**——只核过 `landing.html`
- `dashboard/deck/poster/archdoc` 四个渲染器**未逐行核**，只确认了函数签名与
  `blocks` 分支的形状
