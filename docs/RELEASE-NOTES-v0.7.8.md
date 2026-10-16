# v0.7.8 发布说明 · C6 收口：点击动作统一事件委托

**发布日期**：2026-10-17
**上一版**：v0.7.7（2026-10-12）
**性质**：结构升级（前端）。HTTP 接口、项目数据、动作语义**均未改变**。
顺带修掉一个真点击验证暴露的既有死交互。架构审计 C6 至此关闭，
**审计清单（C1–C8）全部处置完毕**。

---

## 一句话

**106 处内联 onclick 全量迁到 `data-action` + 统一事件委托；审计推迟
迁移的理由（data-* 字符串 vs 数字 id 的 === 失效）用类型签名表解决；
真点击门禁顺带抓出并修掉「工作区芯片点不动」这个早已存在的死交互。**

---

## 为什么推迟了这么久，现在怎么解决的

审计 C6 把「112 处 onclick 迁 data-action」标为有意推迟，原因是硬的：
`data-*` 读出来永远是字符串，而节点 id 是数字——`===` 比较会静默失效，
没有类型通道的委托等于把 106 个动作全部置于串号风险之下。

v0.7.8 的答案是**把类型转换收敛到唯一一点**：`FOX_ACTION_SIGNATURES`
按动作声明每个参数的类型——

| 类型 | 转换 | 用于 |
|---|---|---|
| `number` | `Number(raw)` | 节点 id / 工作区 id / 修订号等数字主键 |
| `number?` | 空缺归 `null` | advanceWs 的「未归属工作区」（id 从 1 起，0 不是合法值） |
| `string` | 原样 | candidate_id / 模板 id / 面板名等本就是字符串的值 |

声明即契约：站点多给一个键、签名多声明一个键，都是 CI 红而不是运行时
静默丢参。**委托层是字符串→类型的唯一转换点**——这正是审计要的
「编译期约束」。

---

## Changed

- 106 处内联 onclick 全量迁移（一次性脚本 `migrate_onclick_to_data_action.py`
  完成：精确字符串 + 次数断言，形状漂移即硬失败）。
- 语义升格：`zoomBy(1.2)` → `zoomIn`；`FoxCanvasProductivity.undo()` →
  `undo`（8 个命名空间调用全部登记进 `window.FoxActions`）；
  `window.open('/classic')` → `openClassic`；classic 的
  `loadProjects();return false;` → 委托层对 `<a>` 一律 preventDefault。
- 小地图是画布部件而非用户命令：click 由 canvas-productivity 直接绑定
  （需要原始事件坐标，不进参数签名通道）。
- 保留内联（指针/键盘层，非 click 动作，继续受登记校验）：`ondblclick`、
  `onpointerdown`（••• 编辑钮）、minimap `onkeydown`。
- 未知动作 → console.error 可见报错（死按钮在开发期暴露，intakeFetchBatch
  教训的终态化）；`closest()` 取最近 data-action，等价替代旧
  `event.stopPropagation()` 语义（内层按钮接管后父级容器动作不再触发）。

## Fixed · 工作区芯片点击失灵（既有缺陷）

真点击门禁在验证 closest 语义时发现：**点击工作区芯片毫无反应**。
事件流追踪显示 pointerdown 落在芯片上、pointerup 落在容器上、click
事件根本不存在——`finishPointerInteraction`（window pointerup 处理器）
**无条件**重渲染工作区导航栏，把按下中的芯片元素整个换掉，Chromium
对被替换的按压元素直接抑制 click。

用 v0.7.7 的前端文件实测确认：**该缺陷早于本版迁移存在**——内联 onclick
时代芯片同样点不动，桌面端点击芯片无法切换工作区（用户可用的替代路径：
命令面板、移动端标签、拖拽成员归属，因此未爆发成反馈）。

修复：重渲染尾巴只对真的发生过指针交互（拖拽/平移/缩放/连线）或状态
有变的收尾执行；纯点击没有需要清理的中间态。真点击门禁由此成为该缺陷
的永久回归门禁。

---

## 门禁

| 门禁 | 拦什么 |
|---|---|
| `test_action_registry.py`（7 条，静态） | onclick 归零；data-action 全部可解析；站点参数键与签名**双向一致**；签名无死声明；派发表委托真实 Module；无内联 DOM poke |
| `test_action_delegation_runtime.py`（2 条，真点击） | 类型契约（number 等值 / string 原文 / number? 空参归 null）；closest 边界（••• 不触发芯片动作）；zoomIn 真实缩放；未知动作报错可见 |
| 变异 `mutate_action_delegation_gates.py` | 拆委托监听 / 拆 number 转换 / 删签名条目 / onclick 回流——**4/4 CAUGHT** |

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **672 passed / 4 skipped**（含本轮重写 7 条静态 + 新增 2 条真点击门禁；e2e 冒烟的 3 个旧 onclick 选择器随迁移同步更新） |
| 变异验证 | 4/4 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.7.8 一致 |

---

## 明确不在这一版

- 112 处 onclick → data-action 之外的键盘可达性整体治理（`<div onclick>`
  之类的角色补全）——独立的无障碍专项，未排期。
- v0.8 方向（桌面壳、云同步）按社区反馈另行安排。
