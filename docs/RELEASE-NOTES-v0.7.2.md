# v0.7.2 发布说明 · IntakeService 提取（结构补丁）

**发布日期**：2026-10-09
**上一版**：v0.7.1（2026-10-08）
**性质**：结构补丁。HTTP 接口、产品行为、项目数据**均未改变**。

---

## 一句话

**按 [ROADMAP](ROADMAP.md) 待办 #11 + #16（合并处理），把设计吸收的全部编排从
HTTP handler 提取为 `IntakeService`，候选键与许可默认值收拢为唯一事实来源。**

---

## Changed

### P1-7 · IntakeService 提取

`app.py` 的 `_Handler` 曾同时承担 HTTP 解析与 intake 编排：抓取、限速、来源
解析、候选存取、许可治理、模板库导入、分块、统计、组件/动效/风格预设导入
全部内联在请求方法里。现在它们住在 `htmlninefox/server/intake_service.py`
的 `IntakeService`（具体类，依赖只走构造参数；审计注：只有一个 adapter 时
不造 Protocol）。`_Handler` 的每个 `_api_intake_*` 方法退化为单行委托。

行为零变化：全部既有 intake 测试原样通过。

### C8 · 候选键与许可默认值唯一化

- 新增 `intake.CandidateKeys`（15 个候选键的常量清单）与 `DEFAULT_LICENCE`；
  写入端 `extract_candidate` 全部走常量。
- 新增 `intake.licence_of(candidate)` 作为许可档位的**唯一读入口**——
  此前 `license_class` 的默认 `"reference"` 散在 5 处（intake.py 4 处 +
  app.py 2 处），键名写错就静默降级治理强度。
- `server/app.py` 不再出现任何 `license_class` 裸读取。

---

## 门禁

| 新增 | 反向验证 |
|---|---|
| `tests/test_candidate_keys.py`（9 条）：写入端键集 == 声明清单（双向）；`licence_of` 三档+缺键行为；server 包零裸许可读取；intake.py 默认值唯一 | 写端多一个未声明键 → 红；默认值改错 → 红；server 加回裸读取 → 红 |
| `tests/test_intake_service_structure.py`（3 条）：handler 零编排原语；intake 方法纯委托；限速器唯一实例 | fetch 编排回流 handler → 红；handler 造第二限速器 → 红 |
| `tests/test_intake_service.py`（5 条）：IntakeService 直属单测（抓取/采纳/分块只读/统计/共享限速器） | —— |
| `scripts/mutate_intake_service_gates.py` | 2/2 CAUGHT |

既有 intake 测试（workbench / page_blocks / licence rule / design intake /
stress）全部原样通过；`test_licence_rule_is_one_rule.py` 与
`test_page_blocks_from_candidate.py` 的注入点随提取更新（stub 从 handler
换到 service）。

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **616 passed / 2 skipped**（68 个测试文件；本轮新增 17 条；Linux CI 预期 617 passed / 1 skipped） |
| 发布元数据 | `check_release_version.py`：v0.7.2 四处一致 |

---

## 明确不在这一版

- C1（Project 锁三种写法）、C5（错误码三处硬编码）、C7（lifecycle 顶层
  作用域）仍按 [ROADMAP](ROADMAP.md) 顺序另行安排。
- 行为零变化：本版没有任何用户可见的新功能或修复。
