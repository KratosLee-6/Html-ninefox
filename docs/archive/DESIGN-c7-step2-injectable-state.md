# C7 第二步：把 2 个裸奔文件变成可注入

状态：**已实现**（第一步，见 [`DESIGN-c7-front-end-kernel.md`](DESIGN-c7-front-end-kernel.md)）。
本文记录第二步的决策与实现结果，并订正计划阶段的两处高估。

## 最重要的一件事：范围比以为的小一半

调查推翻了我们此前的三个前提，其中两个直接改变工作量估算：

| 此前假设 | 实际 | 影响 |
|---|---|---|
| 6 个文件没有 IIFE 包裹 | **6 个都是箭头 IIFE**（`(() => { 'use strict'; … })()`） | 需改造的文件数减半 |
| 13 个文件共享一个全局作用域 | **只有 2 个**：`fox-core.js` 与 `workbench-features.js` | C7 不是拆 13 个文件，是让 2 个文件可注入 |
| fox-core.js 81,375 字符 | 81,957 字符 / 86,804 字节（中文占多字节） | 仅单位差异，无影响 |

已独立复核前两条：逐个文件读前 6 行，11 个是 `(() => {` 开头，只有
`workbench-features.js` 和 `fox-core.js` 是裸的。

**所以 C7 第二步的真实目标不是模块化，是给这 2 个文件做依赖注入。**
其余 11 个文件已经是干净的 IIFE，它们只是**消费者**。

## 全局符号盘点

全局可及符号 197 个（`fox-core.js` 184 + `workbench-features.js` 13），
其中 66 个被其他文件真正引用，约 130 个只是碰巧落在全局词法作用域、不构成耦合。

| 类别 | 数量 | 是否要动 |
|---|---|---|
| 真正的共享可变状态（多文件读**且**多文件写） | **9** | 逐个显式化 |
| 共享只读常量 / 工具函数 | 约 22 | 走 `window.Fox*` 命名空间 |
| 跨文件调用函数与命名空间 | 约 35 | 已经是健康的命名空间设计 |

### 9 个真正的共享可变状态

| 符号 | 声明 | 读 | 写 | 写的方式 | 风险 |
|---|---|---|---|---|---|
| `nodes` | `fox-core.js:104` | 7 个文件 | `lifecycle-projects` | **整体替换** `nodes = nodes.filter(…)` | **极高** |
| `edges` | `fox-core.js:104` | 3 | `lifecycle-projects` | **整体替换** | 高 |
| `state` | `fox-core.js:122` | `workbench-features` | 3 个文件 | 属性赋值 `state.gallery=` | 高（但可机械替换）|
| `camera` | `fox-core.js:103` | `canvas-productivity` | `canvas-productivity` | 整体替换 + 属性写 | 高 |
| `selected` | `fox-core.js:104` | `canvas-productivity` | `canvas-productivity` | 赋值 | 中 |
| `activeWorkspaceId` | `fox-core.js:104` | 2 | 2 | 赋值 | 中 |
| `PALETTE` | `fox-core.js:1091` | `workbench-features` | `workbench-features` | **属性整体替换（猴补丁）** | **高** |
| `activeTab` | `fox-core.js:1122` | — | `workbench-features` | 赋值 | 中 |
| `snapLevel` | `fox-core.js:110` | `canvas-productivity` | `canvas-productivity` | 赋值 | 中 |

`selectedIds` 不在此表：它**只有 `clear/add/delete` 方法调用，没有任何重新赋值**，
是四个已知共享状态里最干净的一个。

## 三条硬顺序依赖（真正的雷）

其余 `window.Fox*` 依赖都带 `?.` 或在函数体内，只有这三条是**顶层立即读**：

| # | 依赖 | 位置 | 违反后果 |
|---|---|---|---|
| 1 | `fox-core.js` → `FoxCanvasEngine` | `fox-core.js:109,110,123` | 前两个静默降级为默认网格；`:123` 的 `create()` 是硬调用，直接 **TypeError 整个内核崩** |
| 2 | `workbench-features.js` → `fox-core.js` 的 `PALETTE` | `workbench-features.js:121,146,172` 顶层赋值 | **ReferenceError**，且 `originalStylesPalette = PALETTE.styles` 连带炸 |
| 3 | `workbench-features.js` → DOM | `workbench-features.js:87-90,535,627` 顶层 `addEventListener` | 元素不存在则 **TypeError**，文件执行中断，后续所有函数不定义 |

**已独立复核 2 和 3**：这三行的缩进是列 0，确认是顶层语句而非函数体内。

`lifecycle-*` 相对 `fox-core.js` 的顺序**理论上可换**——`FoxActions` 表里是
`() => window.FoxProjects.load()` 这类延迟箭头函数，只要不在 `init()` 前触发点击就无关。

## 选哪个切口

### 选 `state` + `PALETTE`，不选 `nodes`

**理由一：一处改动解锁 8 个纯函数。**
`workbench-features.js` 的 13 个符号里有 11 个只依赖 `state` / `PALETTE` /
`api` / `flash` / `$`。把 `state` 变成显式注入后，这些立刻可以在 Node 里喂假数据单测：
`galleryItem`、`galleryTemplateData`、`galleryPageData`、`memoryValueText`、
`memorySummaryMarkup`、`isProjectAdopted`、`applyRecommendedRecipe`、
`ensureCreationRequirement`。**它们现在一个都测不了。**

**理由二：同时拆掉两条硬顺序依赖。**
`PALETTE.layouts = …` 是全代码库唯一一处「跨文件在顶层改写别人对象的属性」，
也是顺序依赖 ② 的唯一成因。改成 provider 注册表（`fox-core` 在 `init()` 里
向 `workbench-features` 拉取 palette 贡献者，或反过来显式调用注册的 hook），
② 立刻消失。DOM 绑定（依赖 ③）同时移进 `fox-core.init()`。

**理由三：`state` 的改造是纯机械替换。**
`state` 虽然是 `const` 对象，但**没有任何文件重新赋值 `state` 本身**——
只改属性（`.gallery` / `.projects` / `.ai` / `.intakeComponents` / `.templates` / `.alliance`）。
改成 `ctx.state` 不涉及「跨文件整体替换」这种会静默丢引用的操作。

**`nodes` 为什么不适合当第一个切口：**
它有 3 处**整体替换**（`fox-core.js:184`、`:1081`、`lifecycle-projects.js:58`），
且 7 个文件持有引用。把 `let nodes = []` 换成 `ctx.nodes = []` 会立刻踩到
「旧引用还指向旧数组」的经典陷阱——必须先把它改成「永不整体替换，只做
原地 `splice`」，那是一次真正的行为重构，风险远高于 `state`。

**次优切口（若想更小）**：只做 `selectedIds`。它是唯一从不整体替换的，
改动面只有 15 处，能让 `canvas-productivity.js` 的选择逻辑
（`selectWithin` / `toggleSelectionMode` / `groupSelection` / `deleteSelection`）
变成纯函数可测。**但只解锁 1 个文件，收益小于 `state`。**

## 四个风险，每一个都要写进实现

1. **（最高）`state` 各键的读取时机早于写入完成。**
   每个键都是 `init()` 里 `await` 出来的，而 `workbench-features` 里有大量同步读
   `state.gallery` 的函数。改成注入后，**每个消费点的「键可能还不存在」兜底都必须保留**。
   极易顺手删掉 `|| []` 之类的兜底，导致 init 竞态下白屏——静默失败，CI 未必抓得到。

2. **`PALETTE` 的属性改写是「猴补丁」语义。**
   `workbench-features.js:172` 覆盖 `PALETTE.styles` 前，`:171` 先把原函数存进
   `originalStylesPalette` 备用。任何「顺手把 `PALETTE` 冻结成 `Object.freeze`」
   的优化都会让 `:171` 之后的逻辑**静默失效**。必须显式设计 provider 注册表，
   而不是简单改成只读。

3. **命名碰撞 `selected`。**
   `fox-core.js:104` 的全局 `selected`（nodeId）与 `lifecycle-intake.js:10` 的
   局部 `selected`（Set）同名不同义。任何按名字批量替换的自动化重构都会改错
   intake 的选择逻辑——本次调查的分析器就在这里踩过一次坑。
   **动手前先把其中一个改名**（建议 intake 那个改成 `intakeSelected`）。

4. **`window.FoxWorkbenchUI` 没有任何消费者。**
   可能是为未来预留，也可能是死代码。C7 第二步**不要顺手删**——先确认有没有
   E2E 测试或动态字符串引用。

## 计划阶段的两处高估，实现时订正

这一节是本文最有用的部分。上面那份分析读起来很有说服力，实现时发现两处判断错了。

### 高估一：可单测的纯函数是 6 个，不是 8 个

`applyRecommendedRecipe` 与 `ensureCreationRequirement` 被算进了「纯函数」。读完实现
才看清：它们改工作区内容，依赖 `membersOf` / `addMaterialToWorkspace` / `nodes` / DOM。
喂一个假 `state` 救不了它们。

真正只依赖 `state`（外加 `esc`）的是六个：

| 函数 | 依赖 | 本轮可单测 |
|---|---|---|
| `galleryItem` | `state.gallery` | ✅ |
| `galleryTemplateData` | 仅入参 | ✅ |
| `galleryPageData` | 仅入参 | ✅ |
| `memoryValueText` | 无 | ✅ |
| `memorySummaryMarkup` | `esc` + `MEMORY_FIELD_LABELS` | ✅ |
| `isProjectAdopted` | `state.memory` | ✅ |
| `applyRecommendedRecipe` | `membersOf` / `addMaterialToWorkspace` | ❌ 改工作区 |
| `ensureCreationRequirement` | `nodes` / DOM / 建节点 | ❌ 改工作区 |

后两个要变成可测，得先把 `membersOf` 与 `addMaterialToWorkspace` 也变成可注入的——
那是比本轮更大的一步，不该混在一起做。

### 高估二：`state` 本身并不需要改造

计划说「把 `const state` 换成可注入的 `ctx.state`」。实际读代码发现**不需要**：
那些纯函数以裸标识符 `state` 引用它，而裸标识符会一路回落到全局对象。
只要测试在沙箱里先放一个 `state`，它们就直接吃到了。

真正挡住测试的不是 `state` 怎么声明，而是**这个文件在加载时就在动手**：
13 行顶层语句（7 处 DOM 绑定、1 处 DOM 调用、3 处对内核 `PALETTE` 的赋值，
外加 1 个在求值时就读 `PALETTE` 的顶层 const）。classic script 的顶层语句在解析时
执行，于是这个文件既装不进空沙箱，也把 `index.html` 的加载顺序变成硬约束。

所以本轮实际做的是**清空顶层**，而不是重写状态模型。`state` 一个字没改。

## 实际做了什么

### workbench-features.js：顶层只剩声明

13 行顶层语句收进两个函数：

- `bindWorkbenchDom()` — 全部 8 处 DOM 绑定
- `registerWorkbenchPalette(PALETTE)` — 三个调色板贡献者

三个调色板 provider 从 `PALETTE.layouts = () => {...}` 改成命名函数声明
（`workbenchPaletteLayouts` / `workbenchPaletteBlocks` / `workbenchPaletteShowcases`），
由注册函数负责赋值。

**刻意保留「保存原实现再叠加」的语义。** 原来的
`const originalStylesPalette = PALETTE.styles;` 必须在赋值前抓到，因为
`PALETTE.styles` 会被整体替换，而替换后的实现末尾还要把原生实现里非分组的
那些项拼回来。把 `PALETTE` 冻结成只读会让这段静默失效——这是设计阶段就写进
风险表的第 2 条，实现时它原样保留。

### fox-core.js：内核显式装扩展层

`init()` 的**最前面**加两行：

```js
registerWorkbenchPalette?.(PALETTE);
bindWorkbenchDom?.();
```

放在 `init()` 里面而不是文件顶层，是被门禁抓出来的，不是想出来的。classic script
的顶层语句在解析时执行，那时 `workbench-features.js` 还没被解析，名字根本不存在；
而 `registerWorkbenchPalette?.(PALETTE)` 里的 `?.` **只挡 null/undefined，
挡不住「标识符未声明」的 ReferenceError**。

> 第一版把这两行放在 `fox-core.js` 文件末尾（`addEventListener` 之前），
> `test_the_file_loads_before_the_kernel` 立刻报
> `LOAD_ERROR:fox-core.js :: registerWorkbenchPalette is not defined`。
> 门禁在提交之前抓住了我自己引入的缺陷。

放最前面还有一个理由：`loadGallery()` 稍后会在 `Promise.all` 里触发
`renderPalette()`，那时调色板必须已经注册好。

## 门禁：14 条，变异 9/9

`tests/test_workbench_features_pure.py`。加载器只给一个假 `state` 和 `esc`——
少给一个，报错会指名道姓说是哪个名字找不到。

**行为断言**（在空沙箱里真跑文件、真调函数、断言真实返回值）：

- 文件装得上，且六个纯函数都还是函数
- `galleryItem` 读注入的 state；找不到返回 `undefined`
- `galleryTemplateData` 的拖拽数据带全 `gallery_id` / `preset` / `intent` / `preview_url`
- `galleryPageData` 同时带住 item 与 page 两层来源
- `memoryValueText` 数组拼接、字符串原样、空值不炸
- `isProjectAdopted` 依 `evidence` 判定；memory 没加载过也不算采用过
- `memorySummaryMarkup` **把值转义**（`&lt;img` 在、`<img` 不在）——漏掉 `esc`
  就是一条注入路径，而它对仓库里其他任何门禁都不可见
- 三个调色板槽位**全部**被替换（探针比身份，不调用 provider）
- 内核**真的调用了**注册函数（装探针替换 callee，跑 init，看有没有被叫到）

**结构性断言**（各一条，都说明为什么它不是文本形状的替代品）：

- 顶层零副作用：逐行累计花括号深度，深度为 0 的行只允许是声明
- 整条链在两种顺序下都装得上：index.html 的真实顺序，以及把扩展层提到最前

### 两条门禁是被变异逼出来的

第一轮变异是 **6/10**。四个 MISSED 里，两条是我的变异写错了，两条是**真的缺门禁**：

| 变异 | 当时结果 | 真实原因 |
|---|---|---|
| C1 顶层又去改 PALETTE | MISSED | 变异只在函数内减了两格缩进，深度仍是 1，根本没搬到顶层 |
| C2 顶层又去绑 DOM | MISSED | 同上 |
| C5 三个槽只注册两个 | MISSED | **缺门禁**：没有任何一条检查「三个都注册了」 |
| C3 内核不再注册 | MISSED | **门禁无效**：它是文本断言，变异删的是注释里那一份，代码行还在 |

C3 那一处最值得记：我原本的门禁写的是
`assert "registerWorkbenchPalette?.(PALETTE)" in core`，而同一串字符也出现在我自己
写的解释性注释里。删掉代码行之后，断言照样成立。**文本断言验证的是字符串出现过，
不是代码跑过。** 换成探针之后才真的抓住。

C5 补的那条门禁也说明了另一件事：少注册一个槽位是**半坏的形状**——版式页看起来完全
正常，只有内容区和风格区悄悄退回内置实现。布尔式检查最容易漏掉这种。

## 一条我一度选择不补、后来又补上的门禁

「注册时机够早」这条性质——也就是 `registerWorkbenchPalette` 若被挪到
`Promise.all` 之后，版式页会丢掉真实模板——我**先是不打算补**的。理由写在当时的
提交说明里：能想到的只有两种，读 `fox-core.js` 断言两行的先后（文本形状的顺序
断言，正是本文刚证伪的那种），或者在 node 里真的把整个应用 boot 起来看调色板
（试过了，`init()` 在沙箱里会抛，代价远超收益）。宁可留一条「未覆盖」，也不
交付一条冒充覆盖的弱门禁。

**后来补上了，因为「boot 不了」是错的结论。** 错的是我的 stub：它把每个请求都
答成 `{}`，`init()` 读到第一个 `.enabled` 就抛。把响应形状修对之后，整条链一路
跑到 `["register", "renderPalette", "renderPalette"]`，顺序属性直接可观测。

补的过程本身又返工了一次，值得记下来：第一版把 `loadGallery` 也换成了记录器，
于是**真实的那次早期渲染消失了**——只剩 `init()` 末尾那次，而注册排在它前面，
于是变异把注册挪到 `Promise.all` 之后，门禁照样绿（C10 首轮 MISSED）。
必须让真的 `loadGallery` 跑：`activeTab` 默认就是 `layouts`，它内部会调
`renderPalette`，那才是「注册太晚会出事」的那一次渲染。

> 教训：**「我试过，走不通」和「走不通」不是同一句话**，尤其当失败发生在
> 夹具而不是被测代码上。stub 崩了要问的是「stub 写错了吗」，不是「这条路不存在」。
> 这和本会话里第三次出现的「我自己工具的负面结论是错的」是同一个模式。

现在的门禁断言的是**实际发生的调用顺序**，配套变异 C10 把注册挪到 `Promise.all`
之后，必须变红——已经验证会红。

## 顺带扫了一遍「还会自己腐坏的门禁」

本会话已经踩到两次同一形状的问题：证书过期（`test_ssrf_tls_pinning.py` 缓存了
有效期 ±1 天的自签证书，满一天就开始失败，报错还长得像产品 bug）、
依赖未声明（`cryptography` 从没进过 pyproject，那条安全门禁在 CI 上一回都没跑过，
只在恰好装了它的本机绿）。既然是同一类，就值得系统扫一遍。

扫了四类，结论：

| 类别 | 结论 |
|---|---|
| 测试引用了未声明的第三方包 | **无**。第一版扫描器误报了 `click` / `playwright` / `python-pptx`，三者都在 pyproject 里——是扫描器的正则写错了，不是仓库漏了 |
| 硬编码日期 / 有效期窗口 | **无会过期的**。列出来的 20 多处全是当数据用的固定时间戳（`created_at` / `fetched_at`），不是有效期逻辑 |
| 仓库里缓存的夹具文件 | `tests/cert/` 未被 git 跟踪（gitignore 覆盖），里面三个 `.old` 是本地垃圾，已清 |
| skip / importorskip / xfail | 三类，逐个查过，**都不构成洞** |

skip 那三类值得展开，因为「绿灯里有个 skip」正是最容易藏东西的地方：

- `test_revision_history.py:138` 的 `skip("Host does not permit symlinks")` 看着
  最危险——它守的是**拒绝指向项目外部的 symlink 修订快照**，一条路径穿越防线。
  但 CI 跑在 ubuntu 上，symlink 可用：**CI 最近一次是 457 passed / 0 skipped**，
  这条门禁在真正算数的地方一直有跑。本地 skip 只是 Windows 没开开发者模式。
- `test_pptx_export.py` 与 `test_v060_visual_evidence_states.py` 的
  `importorskip("pptx")` 看着像「导出验证会静默消失」。但用户可见的那条 pptx
  路径由 `tests/test_ui_e2e_smoke.py` 用标准库 `zipfile` 验（能打开、有
  `[Content_Types].xml`、至少三页），**不依赖 python-pptx，不会 skip**。
  `importorskip` 那两处守的是更深的桥接测试，确实需要这个库。
- 两条 `skipif(node)` 在我自己新写的门禁里，两个 job 都显式装了 node，所以会跑。

> 这条扫一扫**没找到新问题**，如实记下来比「顺手又修了三个」有用。
> 真正修掉的那个（证书过期）已经在上一轮提交里。

## 第四步的准备：`nodes` 整体替换的现状核实（2026-10-05）

第三步要把 `nodes = nodes.filter(...)` 改成原地删除。动手前先回答一个
**容易问反的问题**：今天是「已经有陈旧引用的 bug」，还是「只是未来的风险」？

**结论：是纯未来风险，今天没有 bug。** 依据不是推测，是逐处扫过的：

- 跨时间持有 `nodes` 的只有 `() => nodes` 闭包（`fox-core.js:123` 传给画布引擎的
  `getNodes`），它们**每次重读变量**，替换后自然看到新数组；
- 看起来像「快照」的 8 处（`canvas-productivity.js:367,421`、`fox-core.js:166,318,811`、
  `workbench-ui.js:82,88` 等）全是**函数内的局部** `nodes.filter(...)` / `nodes.map(...)`，
  不跨调用；
- `lifecycle-projects.js:60-61` 在整体替换后**显式清空并重渲染** DOM，不是漏了。

所以第三步不是「修 bug」，是**给一次重构铺网**。

### 铺的网：6 条门禁，变异 8/8

`tests/test_nodes_removal_observers.py`。它不比对写死的清单，而是**把各个持有者
互相比对**——`nodes`、`edges`、`workspaceSnapshot()`：

| 变异 | 形态 |
|---|---|
| N1 / N4 | 算出了新数组**但没赋回去**（「我改成原地了但忘了绑定还指着新数组」的经典形状，**不抛任何异常**） |
| N2 / N5 | 节点清了、指向它们的边没清 |
| N3 | kind 过滤被改窄，连带删错或删漏 |
| N6 | 删了工作区却不清 `activeWorkspaceId`（内核里那**两条**路径都断） |
| N7 | 两条删除路径（内核的 `deleteNodeIds` / lifecycle 的 `removeNodes`）结果不一致 |
| N8 | 删一个**不存在**的项目却把画布清空 |

如果哪次重构让某个持有者跟不上，这 6 条会红。**在那之前，重构没有任何东西可以失败。**

### 这轮门禁自己踩的三个坑（都不是产品的问题）

1. **种子形状错了。** 我把 `project_name` 放在节点顶层，而代码读的是 `x.data.project_name`
   （`addNode` 的 `fox-core.js:405-409`）。过滤器一个都没匹配上，`removeNodes` 报告成功
   却什么都没删——**一个看起来像通过的测试，实际什么都没验**。
2. **夹具没让场景真正发生。** 「删掉当前工作区会清空 `activeWorkspaceId`」那条，
   种子从没设过 `activeWorkspaceId`，它一直是 `null`，两条清理路径都是空操作，
   断言于是怎么都对。**因为setup 没发生而通过的门禁，比没有门禁更糟。**
3. **变异本身有两个是错的。** N6 第一版只删了 `activeWorkspaceId = null` 的**其中一条**
   ——代码里有两条路径通向同一个结果，删一条不是缺陷，门禁保持绿色是**对的**；
   N8 第一版复用了 N1 的变异，而它恰好**产生**那条门禁想看到的「没变化」。

第 2、3 条都指向同一件事：**先问「这个场景真的发生了吗」，再问「门禁为什么没红」。**
负面结果跑得快，所以最容易被提前相信。

## 本轮没做

- `nodes` / `edges` 仍有跨文件**整体替换**（`fox-core.js:184`、`:1081`、
  `lifecycle-projects.js:58`），仍然不能改成注入。要动它必须先改成「永不整体替换」，
  那是一次真正的行为重构。
- `applyRecommendedRecipe` / `ensureCreationRequirement` 仍不可单测（见上文高估一）。
- `window.FoxWorkbenchUI` 仍无消费者，本轮没有顺手删。
- 命名碰撞 `selected`（`fox-core.js:104` 全局 vs `lifecycle-intake.js:10` 局部）未处理。

## 未确认

- `classic.html` 与 `motion-lab.html` 是否加载这 13 个脚本的其他组合，**未检查**。
  只验证了 `index.html:870-882` 这一处。
- `FoxActions` 的 44 个 action 在 HTML 里的实际使用率未统计。
- 上述引用次数（R 值）来自词法近似分析器而非完整 AST，单行多重赋值与
  `for...of` 解构等边缘写法可能仍有偏差。**关键判定已逐行人工复核，R 值当量级看。**
