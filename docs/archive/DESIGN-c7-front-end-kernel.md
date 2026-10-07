# C7 第一步：把共享内核搬出 index.html

状态：已实现，变异验证 10/10 CAUGHT，全量回归通过。

## 要解决什么

C7 是「前端 12 个 classic script 共享顶层作用域、无法单测」这条债的第一步。
在这之前，81,375 字符的内核以 inline `<script>` 的形式住在 `index.html` 里。
测试要碰到它，唯一办法是加载整份文档——那不是单元测试。

抽出来之后，测试可以在裸上下文里**真实加载**这条脚本链并检查它到底定义了什么。

## 改了什么

| 文件 | 变化 |
|---|---|
| `htmlninefox/server/static/fox-core.js` | 新增，81,957 字符（582 字符横幅 + 81,375 字符内核，逐字节搬出） |
| `htmlninefox/server/static/index.html` | 162,247 → 80,891 字符；2192 → 862 行 |
| `htmlninefox/server/app.py` | `STATIC_FILES` 白名单登记 `/fox-core.js` |
| `scripts/extract_front_end_kernel.py` | 机械抽取脚本，带字节校验与拒绝重跑 |
| `tests/test_frontend_kernel_loadable.py` | 4 条新门禁 |
| `tests/test_action_registry.py` | 改为跟随派发表的新位置（原为 3 条红） |
| `scripts/mutate_frontend_kernel_gates.py` | 10 个变异验证 |

`fox-core.js` 挂在 `index.html:879`，即原 inline 块的原位。**script 顺序是敏感的，
不要移动它**——它在 `canvas-engine.js` 之后、五个 `lifecycle-*` 之后。

## 真正的根因：静态资源是显式白名单

`app.py:43` 的 `STATIC_FILES` 是一个手写字典。新脚本写完不登记，`/fox-core.js`
就 404，整个工作台前端全废——**而所有门禁全绿**，因为没有任何门禁去发过一个 HTTP 请求。

这和 v0.6.0 便携包「四个 job 全绿、全部测试通过、一启动就崩」是同一种形状。
所以本轮门禁里最重要的一条不是「内核能不能加载」，而是**「页面要什么，服务端给不给得出，而且给的字节对不对」**。

## 门禁（4 条，全部执行真实代码）

1. `test_fox_core_exists_and_is_not_inline` — 内核是真实文件，不是被搬回页面的 blob
2. `test_fox_core_passes_the_node_syntax_check` — `node --check`
3. `test_front_end_chain_loads_and_every_shared_helper_is_really_defined` —
   按 `index.html` 真实顺序在 node `vm` 裸上下文里加载**整条 13 个脚本的链**，
   然后从一个活着的上下文对象上读回 `typeof`，断言 11 个共享助手全是 `function`、
   2 个命名空间全是 `object`
4. `test_every_script_the_page_asks_for_is_actually_served` — 起真实
   `ThreadingHTTPServer`，对 `index.html` 里每一个 `<script src>` 发真实 HTTP GET，
   断言 200、断言**返回字节与磁盘文件逐字节一致**、断言 `Content-Type` 是 JavaScript

### 为什么第 3 条要加载整条链

`fox-core.js` **不是独立的**。它在顶层调用 `FoxCanvasEngine.create()`，
而 `FoxCanvasEngine` 由 `canvas-engine.js` 定义。只加载 `fox-core.js` 会得到
`ReferenceError`——这是真实的依赖关系，不是测试环境的问题。

顺带一个陷阱：浏览器里 `window === globalThis`。在 `vm` 沙箱里如果
`sandbox.window` 是另一个对象，顶层 `function` 声明会落在 context global 上、
永远看不到 `window.api`，测试就会误判成「助手没定义」。

### 为什么不 grep 源码

`test_fox_core_defines_every_shared_helper` 和 `test_fox_core_publishes_its_namespaces`
这两条**曾经存在，已删除**。它们做的是 `re.search(r"function\s+flash\s*\(", text)`——
验证的是文本形状，不是行为。一行注释就能满足，无害重构还会误报。
这正是 `tests/test_gate_quality_gates.py` 被证伪并移出 `tests/` 的原因。

第 3 条从活上下文里读 `typeof`，是行为断言，注释满足不了它。

## 抽离顺手打出来的红灯：`test_action_registry.py`

全量回归第一轮开头就是三个 `IndexError`。这不是新缺陷，是既有门禁被搬动打脸：

```python
index = _read("index.html")
table = index.split("window.FoxActions = {", 1)[1].split("\n};", 1)[0]
```

派发表跟着内核一起搬到了 `fox-core.js`，而这条门禁把文件路径写死了。
它同时还**少扫了一个文件**——`_real_functions()` 的 `SCANNED` 列表里没有
`fox-core.js`，抽离后内核里所有 `function` 声明对这条门禁而言直接消失了。

改法不是把路径换成 `fox-core.js`（那只是把同一个硬编码搬个地方），而是
`_action_table()` 在 `SCANNED` 里找真正定义派发表的文件，一个都没找到就抛
带扫描清单的 `AssertionError`。下次再搬，只会得到一句人话，不会是三个 IndexError。

**我改过这条门禁，所以它必须重新反向验证**——不然「改完变绿」和「门禁本来就瞎」
看起来一模一样。见下面 K9 / K10。

## 变异验证：10/10 CAUGHT

`scripts/mutate_frontend_kernel_gates.py`。每个变异破坏一种真实故障形态，
对应门禁必须变红。

| 变异 | 形态 | 抓它的门禁 |
|---|---|---|
| K1 | 白名单漏登记 `/fox-core.js`（v0.6.0 形状） | 新 4 |
| K2 | 页面不再加载 `fox-core.js` | 新 1 |
| K3 | 内核被搬回 inline | 新 1 |
| K4 | 共享助手 `flash` 消失 | 新 3 |
| K5 | 内核解析通过但加载即抛错（工作台全白） | 新 3 |
| K6 | 内核语法错误 | 新 2 |
| K7 | 白名单条目指向了别的文件（200 但内容错） | 新 4 |
| K8 | 命名空间不再暴露 | 新 3 |
| K9 | 派发表漏登记被引用的动作（S20 死按钮形状） | `test_every_referenced_action_resolves` |
| K10 | 派发表条目不再委托给 `Fox*` Module | `test_registry_entries_point_at_real_fox_modules` |

K9 删的是 `intakeFetchBatch:` 那一行——就是 S20 期间「批量抓取」变死按钮、
全绿 CI 没人发现的原始缺陷。K9/K10 的存在理由不是「顺手也测一下」，
而是**因为我在本轮改过这条门禁**：一个改过的门禁如果不反向验证，
和从来没瞎过的门禁在结果上无法区分。

### 两条自持纪律

- **变异没生效 = 硬失败，不记 MISSED。** 本轮 K5 连续两次 HARD FAIL
  （第一次找 `//` 行、第二次找 `\n*/\n`，而实际横幅结尾是 `\n */\n` 带前导空格）。
  记成 MISSED 会凭空造出一条「门禁无效」的假结论。改完定位才拿到 10/10。
- **还原用预先读到的字节**，不走 `git checkout`——本仓库有用户未提交的
  `D SKILL.md` 等 4 项遗留，任何 `git checkout --` 都可能吃掉它们。

本轮让「绿灯」这件事第一次有了牙齿：C7 之后，一条全绿的 CI 结果至少意味着
①13 个前端脚本在裸上下文里真的能跑完，②11 个跨文件共享助手真的存在，
③页面要的每个脚本服务端都真的发得出且字节正确，④我改过的门禁都反向验证过。

还差的那一半要说清楚：这些是**加载级**与**可达级**的证据，不是**行为级**。
用户在界面上点一下有没有反应，仍然只有 Playwright 侧的 e2e 与视觉证据在管。
UI 端到端 smoke 是下一棒。

## 本轮没有解决的

- 12 个外部 `.js` 之间的共享状态（`nodes` / `state` / `selected` / `selectedIds`）
  仍是无声明全局。现在它们**可以被加载和检查了**，但要做依赖注入式单测还需要
  显式的状态对象——那是 C7 的第二步。
- `fox-core.js` 里 `renderInspector` / `renderPalette` / 画布拖拽这些重 DOM 路径
  在裸上下文里被 stub 挡着，没有真被验证过。它们的门禁在 Playwright 一侧
  （`e2e_verify.py` 22/22 与视觉证据采集）。在这里假装单测它们，就是那条
  「在坏代码上全绿」的陷阱。
- 6 个文件仍未 IIFE 包裹：`canvas-engine.js`、`canvas-productivity.js`、
  `interaction-system.js`、`motion-system.js`、`workbench-features.js`、
  `workbench-ui.js`。
