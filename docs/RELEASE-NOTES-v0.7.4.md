# v0.7.4 发布说明 · ExportError 状态随错误声明（C5）

**发布日期**：2026-10-11
**上一版**：v0.7.3（2026-10-11）
**性质**：结构补丁。HTTP 接口、产品行为、项目数据**均未改变**。

---

## 一句话

**按 ROADMAP 待办 C5：ExportError 自带 HTTP 状态（raise 处即声明处），
app.py 的 18 条硬编码状态表拆除——「新增错误码忘加表就静默变 500」的
通道不存在了。**

---

## Changed

- `ExportError` 新增 `status: int = 400` 字段：HTTP 状态在 raise 处声明，
  而不是由 adapter 侧的 18 条硬编码表推回。
- `StudioApplication._export_error`：底层 StoreError 的状态在转换为
  ExportError 时随行（不再丢失）；未知意外错误的兜底显式 500。
- `_Handler._export_store_error`：直接消费 `error.status`。

行为等价性由 `tests/test_error_catalogue.py` 逐条锁定：旧表 18 条的
状态在 raise 处声明后逐一保持；`export_failed` 兜底仍为 500。

---

## 门禁

| 新增 | 覆盖 |
|---|---|
| `test_error_catalogue.py`（6 条） | ExportError 状态声明与默认；底层状态随行；兜底 500；app.py 无硬编码状态表 + `.get(code, 500)` 兜底 |

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **631 passed / 2 skipped**（68 个测试文件；本轮新增 6 条；Linux CI 预期 632 passed / 1 skipped） |
| 发布元数据 | `check_release_version.py`：v0.7.4 四处一致 |

---

## 明确不在这一版

- C1（Project 锁三种写法）、C7（lifecycle 顶层作用域）仍按
  [ROADMAP](ROADMAP.md) 顺序另行安排。
