# Html九尾狐 架构深化扫描：v0.6.0 基线

- 扫描日期：2026-09-29
- 基线：`0200618`（v0.6.0 设计吸收流水线 + 可编辑 PPTX 刚落库）
- 方法：[`mattpocock/skills`](https://github.com/mattpocock/skills) 的 `improve-codebase-architecture` + `codebase-design`
- 上一篇同方法审计：[AUDIT-MATTPOCOCK-20260920](AUDIT-MATTPOCOCK-20260920.md)（其 P1/P2 已在 RC3-A ～ RC3-E 消化，不重复列出）

## 结论

上一轮审计的问题**已经不在了**——应用用例 seam、durable write、前端生命周期 Module 都已落地。本轮扫描的重点是 v0.6 整条吸收流水线叠加之后**新长出来的接缝**。

共 8 个深化候选，**全部未实施**。扫描途中另撞上一个真实缺陷，已修。

> 本文档是 `improve-codebase-architecture` 技能的第一阶段产物。该技能的流程是「出报告 → 选定 → grilling 逐条推敲 → 才实现」，因此报告本身不代表任何代码改动。

## 逐项状态

| # | 候选 | 强度 | 状态 |
|---|---|---|---|
| 🐛 | `intakeFetchBatch` 未定义，「批量抓取」按钮死链 | — | ✅ **已修**（`0cf99b8`） |
| C2 | Artifact 写回协议复制 3 份，其中 2 份漏持久化 | Strong | ✅ 已修（写回协议收进单一拥有者） |
| C1 | 幻灯片编辑用例住在 HTTP Adapter，锁不变量无归属 | Strong | ❌ 未做 |
| C3 | 竞态守卫 4 份、3 种形状，Slides 完全没写 | Strong | ❌ 未做 |
| C4 | 「Explicit Requirement + Project Memory → 选定上下文」被实现两次 | Strong | ❌ 未做 |
| C5 | Export 失败语义在三个 Module 间被翻译三次 | Strong | ❌ 未做 |
| C6 | inline `onclick` 动作名无编译期约束，靠 44 个手写 shim 连线 | Worth exploring | ⚠️ **已修一半**（派发表 + 静态门禁；事件委托推迟） |
| C7 | 真实 Interface 是 `index.html` 的全局可变状态 | Speculative | ❌ 未做 |
| C8 | 设计吸收 Candidate 是松散字典，许可档位靠默认值兜底 | Worth exploring | ❌ 未做 |

## 🐛 已修：批量抓取死按钮

`index.html` 用 `onclick="intakeFetchBatch()"` 调用了一个**从未定义**的全局函数；`FoxIntake.fetchBatch` 明明存在于 `lifecycle-intake.js`，只是没接到全局名上。点击必然 `ReferenceError`，于是 S04「多 URL 批量（≤10 条逐条容错）」这条 v0.6.0 主线能力**没有任何用户可达路径**，而服务端与其测试全绿。

这是「能力在服务端实现齐备，却没有用户可达路径、也没有测试点击过入口」的**第三例**（前两例：S17 的 deck 别名、S20 的 PPTX 下拉缺项）。

## C2 · Artifact 写回协议复制 3 份（已修）

「一个 Artifact 前进到新 Revision 后必须同步若干处」是一条被复制 3 遍的协议，三份实现互不一致：

| 实现 | `node.data.revision` | `#rev-` 徽标 | iframe 破缓存 | `renderInspector` | localStorage | 服务端快照 | `FoxProjects.load` |
|---|---|---|---|---|---|---|---|
| `revisions.js` sendFeedback | ✓ | ✓ | ✓ | ✓ | **✗** | **✗** | ✓ |
| `slides.js` save | ✓ | ✓ | ✓ | ✓ | **✗** | **✗** | **✗** |
| `generation.js` rerun | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | **✗** |

> 本节初版把 `revisions.js` 记为「已持久化」，是错的——那一处 `persistWorkspaceNow()` 属于 `mutate()`（restore 路径），不在 `sendFeedback` 里。修正后是 **3 份实现中有 2 份完全没持久化**。

**可复现的用户可见后果**：页面刷新时画布优先从 localStorage 的 `fox-canvas-v3` 恢复（`index.html` 的 `applyWorkspaceSnapshot` 入口）。`sendFeedback` 与 `slides.save` 改了内存里的 revision 号却没写 localStorage，**刷新后用户看到旧 rev 号，而服务端 Artifact 已是新 rev**。而「编辑幻灯片」正是 v0.6.0 刚对外宣称的核心能力（成果 G4）。

**修法**：协议收进唯一拥有者 `window.FoxRevisions.advanceNodeRevision(nodeId, revision, options)`，由它决定是否破缓存预览、是否重绘检查器、是否持久化、是否刷新项目列表。三个调用点各自只留业务语义。

修的过程中有两点必须记下来：

1. **只调 `persistWorkspaceNow()` 是不够的**。它只做 `PUT /api/workspace`，**不写 localStorage**，而刷新路径读的是 localStorage。拥有者必须先 `save()`（同步写 localStorage + 排队防抖的服务端写入）再 `await persistWorkspaceNow()`（立即提交）。第一版修复漏了这一半，是回归测试抓出来的。
2. **回归测试本身一度是假的**。最初用 `page.add_init_script("localStorage.clear()")` 隔离用例，但它会在**每次导航包括 reload** 时执行——正好把被测对象擦掉，测试无论修复在与不在都通过。去掉它之后测试才真正咬住这个缺陷。

回归门禁 `tests/test_artifact_revision_writeback.py`：一条断言协议只有一份实现（其他文件不得再拼 `#rev-${` + `#frame-${` 的组合），一条走「生成 deck → 改幻灯片 → 刷新 → revision 不得回退」。第二条已做反向验证：完全关掉持久化即变红，报 `期望 1，实际 0`。

## C6 动作名派发表（已修，事件委托另议）

修死按钮的方式曾是**补上第 45 个手工转发 shim**——正是本节要消除的形状。已改正：

44 个手写的 `function foo(){ return window.FoxBar.foo(); }` 转发函数收成**唯一派发表** `window.FoxActions`，全局名由它统一挂出。新增 `tests/test_action_registry.py`（4 条）：

- 派发表规模不得缩水（≥40 条），防止有人直接删条目绕过门禁；
- **任何被 HTML / 模板字符串引用的动作名都必须能解析**——引用了没登记的名字，点击时只会抛 `ReferenceError`，而服务端、单元测试与 CI 全绿。这正是 `intakeFetchBatch` 死按钮的形状；
- 每条登记项须委托给某个 `window.Fox*` Module，少数纯 UI 工具动作（打开文件选择器、新窗口打开）例外且写明理由；
- 动作属性里不得再出现内联 DOM 操作（`document.querySelector(...).click()` 已改为具名的 `openZipPicker()`）。

门禁已做反向验证：删掉 `intakeFetch` 的登记项后立刻报出「被引用但没有登记」。

顺带修掉 `esc()` 漏转义单引号（`index.html`）——它的结果会被塞进 `onclick="...('${esc(id)}')"` 这类 JS 字符串。当前 `candidate_id` 被服务端正则限制为 `[a-z0-9.-]`，所以**不是可利用漏洞**，但它会误导后来者。

**未做（有意推迟）**：把 112 处 `onclick` 字符串整体迁到 `data-action` + 事件委托。测量下来参数形态有 6 类（无参 44 / 单 id 32 / 字符串参 8 / `stopPropagation` 组合 5 / 内联 DOM 1 / event 传参 2 / 多参 4），其中 `data-*` 取值一律是字符串而节点 id 是数字，`===` 比较会失效；再加上多参与 `stopPropagation` 语义，132 处迁移的每一处都是引入回归的机会。**派发表 + 静态门禁已经把缺陷类堵死了**（漏登记会在 CI 失败，而不是在用户点击时失败），事件委托留作后续可独立进行的 DOM 纯净化。

## 其余候选要点

- **C1**：`app.py` 内 24 行编排了完整的一次 Artifact 修订（锁、`expected_revision` 409、读产物、应用编辑、提交 Revision），与 Restore 属同类领域用例，但 Restore 有三个 adapter。全仓锁有**三种写法并存**：装饰器（`pipeline.py:331,410`）、手写 `with`（`application.py:532`、`storage.py` ×7）、以及装饰器与 `with` 叠加。根因是 `RestoreRunner` 的 Interface 未声明「被调方持有 Project 锁」。
- **C3**：`#tl-status` / 竞态守卫在 exports（token + stale 闭包）、revisions（自增序号）、generation（Map + abandoned）、slides（**只有 busy，无 stale 守卫**）四处各造各的。Slides 缺失导致可复现串号：保存进行中切换弹窗，前一个 deck 的 revision 号会写进新 deck 的节点。
- **C4**：`_prompt_and_inputs`（Adapter）与 `_prepare_generation`（application）是逐字复制；`memory_overrides → preset` 的解析在 Analyze 与 Generate 各写一遍。测试各断言一半，**没有任何断言要求两者一致**——工作台展示的推荐与实际生成的版式可以静默漂移。
- **C5**：`StoreError` 把 HTTP 状态码焊进持久化错误类型；`exporting.py` 19 处 raise 各自硬写状态码；`app.py` 再用 19 条硬编码表推回来。新增错误码忘了加表就静默变 500。
- **C7**：6 个 `lifecycle-*.js` 以经典脚本加载，共享顶层作用域；`nodes` 被 8 个文件读写 45 处，`state.*` 无任何声明约束（`state.intakeComponents` 在对象字面量里根本不存在）。直接后果：这些文件无法被单元测试。收益最大、风险也最高。
- **C8**：`intake.py` 写 15 个候选键，散在 5 处用 `.get(键, 默认)` 读回，`license_class` 在三处默认 `"reference"`。键名写错会静默降级许可档位而无测试失败。**注意：今日只有 HTTP 一个 adapter，不要顺手造 Protocol**（一个 adapter = 假想 seam，两个 = 真 seam）。

## 建议顺序

1. **C2** ✅ 已完成（写回协议单一拥有者 + 刷新后 revision 不回退的回归门禁）
2. **C3**（串号是可复现缺陷；C2 完成后原语有挂载点——C2 顺带把 slides 的 `draft.nodeId` 在 await 前锁定，串号的一半已经堵上，但 4 套守卫机制仍未统一）
3. **C6**（止损，别再让它变大）
4. **C1**、**C4**、**C5**（结构性债，无紧急故障）
5. **C7**（收益最大、迁移成本未量化，最后评估）
6. **C8**（与 v0.6.x 技术债清单的 P1-7 合并处理）

## 确认健康、不要动的部分

- `exporting.py` 的浏览器探测 / 分页模型 / 报告组装：调用者只交一个 normalized 请求，深度足够。
- `tests/conftest.py` 的 `WorkbenchServer`：RC3-B1 收得干净，测试启动样板已不再是问题。
- `application.py` 的 request/result 包装：即使内部载荷仍是字典，Interface 方向是对的。
- `motion-system.js`（99 行）与 `canvas-engine.js`（258 行）：把动效与画布几何规则全关在内部，是前端**真正深的两个 Module**。RC3-E 按生命周期拆分方向是对的，问题出在拆分后新长出来的接缝上。
