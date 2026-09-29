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
| C2 | Artifact 写回协议复制 4 份，其中 2 份已违约 | Strong | ❌ 未做（**Top 推荐**） |
| C1 | 幻灯片编辑用例住在 HTTP Adapter，锁不变量无归属 | Strong | ❌ 未做 |
| C3 | 竞态守卫 4 份、3 种形状，Slides 完全没写 | Strong | ❌ 未做 |
| C4 | 「Explicit Requirement + Project Memory → 选定上下文」被实现两次 | Strong | ❌ 未做 |
| C5 | Export 失败语义在三个 Module 间被翻译三次 | Strong | ❌ 未做 |
| C6 | inline `onclick` 字符串 seam：44 个手工 shim | Worth exploring | ⚠️ **方向反了** |
| C7 | 真实 Interface 是 `index.html` 的全局可变状态 | Speculative | ❌ 未做 |
| C8 | 设计吸收 Candidate 是松散字典，许可档位靠默认值兜底 | Worth exploring | ❌ 未做 |

## 🐛 已修：批量抓取死按钮

`index.html` 用 `onclick="intakeFetchBatch()"` 调用了一个**从未定义**的全局函数；`FoxIntake.fetchBatch` 明明存在于 `lifecycle-intake.js`，只是没接到全局名上。点击必然 `ReferenceError`，于是 S04「多 URL 批量（≤10 条逐条容错）」这条 v0.6.0 主线能力**没有任何用户可达路径**，而服务端与其测试全绿。

这是「能力在服务端实现齐备，却没有用户可达路径、也没有测试点击过入口」的**第三例**（前两例：S17 的 deck 别名、S20 的 PPTX 下拉缺项）。

## C2 · Artifact 写回协议复制 4 份（Top 推荐）

「一个 Artifact 前进到新 Revision 后必须同步四处」是一条被隐式复制 4 遍的协议，四份实现各不相同：

| 实现 | `node.data.revision` | `#rev-` 徽标 | iframe 破缓存 | `renderInspector` | 持久化 Workspace |
|---|---|---|---|---|---|
| `lifecycle-revisions.js` sendFeedback | ✓ | ✓ | ✓ | ✓ | **✗** |
| `lifecycle-slides.js` save | ✓ | ✓ | ✓ | ✓ | **✗** |
| `lifecycle-generation.js` rerun | ✓ | ✓ | ✓ | ✓ | ✓ |
| `index.html` renderNode | — | — | ✓ | — | — |

**可复现的用户可见后果**：`workspaceSnapshot()`（`index.html`）整体序列化 `nodes`，`node.data.revision` 就在里面。`slides.js` 与 `sendFeedback` 改了内存里的 Revision 号却没调 `save()`（`lifecycle-slides.js` 全文仅 `:41 async function save()` 一处命中）。**刷新页面后用户看到旧 rev 号，而服务端 Artifact 已是新 rev。**

而「编辑幻灯片」正是 v0.6.0 刚对外宣称的核心能力（成果 G4）。

**排第一的理由**：唯一一个既有真实用户可见缺陷、又修复面很小（一个 Module、四个调用点）的候选。做完之后 C3 的竞态原语有了一个天然挂载点。

## C6 方向反了（需优先止损）

修死按钮的方式是**补上第 45 个手工转发函数**——而 C6 说的恰恰是别这么干：89 处 inline `onclick` 靠 44 个手写 shim 连线，HTML 字符串与这份清单之间**没有任何编译期约束**，死 shim 正是这么来的。

我用治理这个问题的手段，加重了这个问题的规模。当前实测：130 个顶层全局函数 / 89 处 inline `onclick`。建议在规模继续扩大前改为 `data-action` + 事件委托，全局名由一个派发表统一提供。

## 其余候选要点

- **C1**：`app.py` 内 24 行编排了完整的一次 Artifact 修订（锁、`expected_revision` 409、读产物、应用编辑、提交 Revision），与 Restore 属同类领域用例，但 Restore 有三个 adapter。全仓锁有**三种写法并存**：装饰器（`pipeline.py:331,410`）、手写 `with`（`application.py:532`、`storage.py` ×7）、以及装饰器与 `with` 叠加。根因是 `RestoreRunner` 的 Interface 未声明「被调方持有 Project 锁」。
- **C3**：`#tl-status` / 竞态守卫在 exports（token + stale 闭包）、revisions（自增序号）、generation（Map + abandoned）、slides（**只有 busy，无 stale 守卫**）四处各造各的。Slides 缺失导致可复现串号：保存进行中切换弹窗，前一个 deck 的 revision 号会写进新 deck 的节点。
- **C4**：`_prompt_and_inputs`（Adapter）与 `_prepare_generation`（application）是逐字复制；`memory_overrides → preset` 的解析在 Analyze 与 Generate 各写一遍。测试各断言一半，**没有任何断言要求两者一致**——工作台展示的推荐与实际生成的版式可以静默漂移。
- **C5**：`StoreError` 把 HTTP 状态码焊进持久化错误类型；`exporting.py` 19 处 raise 各自硬写状态码；`app.py` 再用 19 条硬编码表推回来。新增错误码忘了加表就静默变 500。
- **C7**：6 个 `lifecycle-*.js` 以经典脚本加载，共享顶层作用域；`nodes` 被 8 个文件读写 45 处，`state.*` 无任何声明约束（`state.intakeComponents` 在对象字面量里根本不存在）。直接后果：这些文件无法被单元测试。收益最大、风险也最高。
- **C8**：`intake.py` 写 15 个候选键，散在 5 处用 `.get(键, 默认)` 读回，`license_class` 在三处默认 `"reference"`。键名写错会静默降级许可档位而无测试失败。**注意：今日只有 HTTP 一个 adapter，不要顺手造 Protocol**（一个 adapter = 假想 seam，两个 = 真 seam）。

## 建议顺序

1. **C2**（真实缺陷 + 修复面小）
2. **C3**（串号是可复现缺陷；C2 完成后原语有挂载点）
3. **C6**（止损，别再让它变大）
4. **C1**、**C4**、**C5**（结构性债，无紧急故障）
5. **C7**（收益最大、迁移成本未量化，最后评估）
6. **C8**（与 v0.6.x 技术债清单的 P1-7 合并处理）

## 确认健康、不要动的部分

- `exporting.py` 的浏览器探测 / 分页模型 / 报告组装：调用者只交一个 normalized 请求，深度足够。
- `tests/conftest.py` 的 `WorkbenchServer`：RC3-B1 收得干净，测试启动样板已不再是问题。
- `application.py` 的 request/result 包装：即使内部载荷仍是字典，Interface 方向是对的。
- `motion-system.js`（99 行）与 `canvas-engine.js`（258 行）：把动效与画布几何规则全关在内部，是前端**真正深的两个 Module**。RC3-E 按生命周期拆分方向是对的，问题出在拆分后新长出来的接缝上。
