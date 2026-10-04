# C7 第二步：把 2 个裸奔文件变成可注入

状态：设计已定，尚未实现。本文基于对 13 个脚本的词法作用域分析
（`docs/DESIGN-c7-front-end-kernel.md` 是第一步，已落地）。

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

## 交付标准

C7 第二步完成的判据，与前几步同形——**不是「改完了」，是「能证明」**：

- `workbench-features.js` 那 8 个纯函数有 Node 单测，喂假 `state` 就能测
- 三条硬顺序依赖各自有一条门禁证明「它不再依赖加载顺序」：
  把 `workbench-features.js` 提到 `fox-core.js` 之前加载，页面仍然正常
- 改造后的门禁必须被变异验证：故意删掉一个注册项、把一个 provider 改成返回空、
  让 `state` 某个键晚于消费者初始化——每一条都要变红
- 全量回归 + `e2e_verify.py` 22/22 不退化
- 涉及 `fox-core.js` 的任何改动，都要连带重跑
  `scripts/mutate_frontend_kernel_gates.py`（10/10）

## 未确认

- `classic.html` 与 `motion-lab.html` 是否加载这 13 个脚本的其他组合，**未检查**。
  只验证了 `index.html:870-882` 这一处。
- `FoxActions` 的 44 个 action 在 HTML 里的实际使用率未统计。
- 上述引用次数（R 值）来自词法近似分析器而非完整 AST，单行多重赋值与
  `for...of` 解构等边缘写法可能仍有偏差。**关键判定已逐行人工复核，R 值当量级看。**
