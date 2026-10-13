# v0.7.5 发布说明 · C7 收口：全局状态声明约束

**发布日期**：2026-10-12
**上一版**：v0.7.4（2026-10-12）
**性质**：结构补丁。HTTP 接口、产品行为、项目数据**均未改变**。
架构审计的结构性待办至此全部关闭（C6 事件委托维持有意推迟）。

---

## 一句话

**审计 C7 的最后一块：工作台全局共享 `state` 从「写一半的字面量」变成
七键集中声明 + 只读 `FoxState` 暴露，静态双向镜、IIFE 作用域锁、执行级
核查三面夹击；ROADMAP 待办表清零。**

---

## 缺陷原貌（审计 C7 的具体形态）

六个 lifecycle-*.js 与内核共享一个 `state` 对象，字面量只声明了一半：
`templates / gallery / projects / alliance / ai / memory` 六键，而
lifecycle-intake 直接往里塞 `state.intakeComponents`——这个键在字面量里
**根本不存在**，palette 的读取方只能写 `(state.intakeComponents || [])`
猜形状。读取方与写入方之间没有任何约束，键名写错要等用户打开界面才会
发现，CI 全绿。

---

## Changed

- **七键集中声明，声明即默认值**：`intakeComponents: []` 入表；读取方的
  防御性猜测撤除（声明保证形状，留着猜测等于承认声明没用）。
- **`window.FoxState`（只读冻结）**：声明的可执行形态，`keys()` /
  `value(key)` 供门禁与扩展层核查。没有写入口——写仍然只经 `state`
  本身，核查面不是第二条数据通道。
- **作用域锁**：六个 lifecycle 文件「剥掉注释后恰好一个顶层 IIFE」成为
  不可回退约束，审计里「经典脚本共享顶层作用域」的回归通道焊死。

---

## 门禁（tests/test_frontend_state_schema.py，5 条）

| 门禁 | 拦什么 |
|---|---|
| 静态·引用必有声明 | 源码里每一次 `state.<key>` 引用都必须对着声明（审计原始缺陷形态） |
| 静态·声明必被引用 | 死声明让 schema 变成装饰，禁止 |
| 静态·影子清单双向诚实 | 局部 `state` 影子必须显式登记（lifecycle-generation 的每节点状态、workbench-ui 的徽标字符串），登记必须与事实一致 |
| 静态·IIFE 作用域锁 | 六个 lifecycle 文件单顶层 IIFE 不可回退 |
| 执行级·运行时核查 | 真实脚本链在裸上下文加载后：运行时键 == 声明键、默认形状正确、FoxState 冻结（宽松态赋值静默失效也按语义判定，不靠异常） |

变异验证 `scripts/mutate_state_schema_gates.py`：未声明键被引用 /
声明删键 / 顶层泄漏 var——**3/3 CAUGHT**。

---

## ROADMAP 清账（表与现实终于一致）

待办表 10–17 行逐项核实后全部关闭，表已重写为关闭记录：

- **P1-6** SSRF 连接级 IP 绑定：`_default_transport` 按校验过的地址建
  pinned opener，逐跳独立绑定 + 取回后重绑定检查（本机核实）。
- **P1-7 / C8**：v0.7.2。
- **C3** slides 竞态：`draft.request` stale 守卫（与 revisions 守卫同构）
  + await 前锁 `draft.nodeId`（本机核实）。
- **C4** 逐字复制：`_prepare_generation` 已并入 `_prompt_and_inputs`
  单一实现（本机核实）。
- **C5 / C1**：v0.7.4。
- **C7**：本版（两步内核工作在 v0.6.4，声明约束在本版）。

唯一维持推迟：**C6** 事件委托（112 处 `onclick` 迁 `data-action`，
`data-*` 字符串与节点 id 数字类型不匹配问题未解）。

审计文档 `AUDIT-ARCHITECTURE-20260929.md` 的状态列已同步订正。

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **650 passed / 4 skipped**（含本轮新增 5 条门禁；Playwright 浏览器链路在套件内，工作台启动路径已覆盖） |
| 变异验证 | `mutate_state_schema_gates.py` 3/3 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.7.5 一致 |

---

## 明确不在这一版

- C6 事件委托（有意推迟，理由见 ROADMAP）。
- v0.8 方向（桌面壳、Word 导出、生态）按社区反馈另行安排。
