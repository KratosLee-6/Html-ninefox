# v0.7.4 发布说明 · C5 + C1 结构修复 + 模板渲染一致性

**发布日期**：2026-10-12
**上一版**：v0.7.3（2026-10-11）
**性质**：结构补丁。HTTP 接口与项目数据**未改变**。行为变化仅一处且是修复：
装有可选 `templates` extras（jinja2）的环境下，landing/infographic 的生成
不再被 v0.2 遗留模板截走，回归原生生成器——预览与成品在任何依赖环境下
给出同一种页面。

---

## 一句话

**按 ROADMAP 待办 C5 + C1，外加一条 CI 看不见的真实缺陷：
ExportError 自带 HTTP 状态（raise 处即声明处），app.py 的 18 条硬编码
状态表拆除；四个 Runner 接口声明 Project 锁拥有权；可选依赖 jinja2
不再让「预览一个样、生成另一个样」。**

---

## Changed

**C5 · ExportError 状态随错误声明（raise 处 = 声明处）**

- `ExportError` 新增 `status: int = 400` 字段：HTTP 状态在 raise 处声明，
  而不是由 adapter 侧的 18 条硬编码表推回。
- `StudioApplication._export_error`：底层 StoreError 的状态在转换为
  ExportError 时随行（不再丢失）；未知意外错误的兜底显式 500。
- `_Handler._export_store_error`：直接消费 `error.status`。

**C1 · Runner 接口声明 Project 锁拥有权**

- 四个 Runner TypeAlias（GenerationRunner / FeedbackRunner / RestoreRunner /
  ExportRunner）后的字符串声明「运行方持有 Project 锁」，消除三种锁
  写法并存的所有权歧义。行为不变——`Studio.restore` 的锁包裹保留
  （可注入测试替身无需自行加锁）。

**模板渲染一致性（CI 不可见的环境分叉）**

- 可选依赖 jinja2（extras `templates`）一旦安装，`GenerateExpert` 第 2
  路径用 v0.2 遗留的 `templates/landing.html`（`--primary` 变量制、无
  `--fox-*` 设计令牌、无动效层）截走 landing/infographic 生成——同一
  模板 ID，工作台预览（永远走原生生成器）与成品给出两种页面，且只在
  装了 extras 的机器上发生。既有门禁
  `test_preview_and_generation_agree_on_a_user_template` 在这样的机器上
  如实变红，暴露了缺陷。
- 按 v0.6-S13 deck 先例修复：`_INTENT_TEMPLATE_ALIAS_NO_FALLBACK`
  登记全部可预览意图 + infographic（七个意图忠实），删除
  `templates/landing.html`。任何依赖环境下 landing/infographic 都产出
  原生生成器页面。

---

## 门禁

| 新增 | 覆盖 |
|---|---|
| `test_error_catalogue.py`（6 条） | ExportError 状态声明与默认；底层状态随行；兜底 500；app.py 无硬编码状态表 + `.get(code, 500)` 兜底 |
| `test_lock_ownership.py`（3 条） | 四接口锁声明存在；并发 restore 不损坏状态；Studio.restore 锁包裹存在 |
| `test_template_rendering_agreement.py`（3 条） | landing/infographic 行为级必走原生栈；可预览意图不得有 Jinja2 别名/模板文件；遗留模板不得回包 |

变异验证：`scripts/mutate_template_agreement_gates.py`——拆忠实集合 /
复活遗留模板 / 完整回到缺陷现场，**3/3 CAUGHT**。

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机，装有 jinja2——缺陷环境本身） | **643 passed / 2 skipped**（含本轮新增 3 条门禁；此前该环境如实红过 1 条，即本版修的缺陷） |
| 变异验证 | `mutate_template_agreement_gates.py` 3/3 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.7.4 四处一致 |

---

## 明确不在这一版

- C7（lifecycle 顶层作用域）按 [ROADMAP](ROADMAP.md) 顺序另行评估。
