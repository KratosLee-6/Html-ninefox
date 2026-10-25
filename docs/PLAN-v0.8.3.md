# v0.8.3 迭代计划 · PPTX 反向拆解 + 键盘可达性 + Tauri 决策

**制定日期**：2026-10-24（v0.8.2 已于 10-20 发版——见步骤 0 的勘误）
**性质**：版本规划。设计依据：[DESIGN-REVERSE-INTAKE.md](DESIGN-REVERSE-INTAKE.md)
（2026-10-18 KX 已定）与 [PLAN-v0.8.md](PLAN-v0.8.md) §v0.8.3。

---

## 步骤 0 · v0.8.2 发版（已了结 · 2026-10-24 勘误）

交接文档记载的「13 提交未推送、tag 未打」是当时另一份克隆的滞后状态：
fetch 核实 **v0.8.2 已于 2026-10-20T13:40Z 完整发布**——main=`793f62b`、
tag `v0.8.2`、Release 含 wheel / Win·macOS·Linux 全平台安装包 / 截图 /
品牌视频共 32 个资产。本机 clone 于 10-24 对齐 origin/main（内容逐字节
一致，仅历史哈希不同），无待办。

---

## 一、PPTX 反向拆解适配器 ⭐（已完成 · 2026-10-24）

**用户场景**：手里只有一份别家的 PPT——页序、标题、要点、备注都在，
但拆不开。目标：上传 .pptx → 统一 `intake_outline` → 既有提案层 →
审核台 → 采纳生成，与 DOCX 导入同一条管线，零新渲染路径。

### 交付明细（全部实测）

| 件 | 状态 | 门禁 |
|---|---|---|
| `htmlninefox/pptx_import.py` | ✅ | 解析合同 **15 条**（含 locator 回读比对、合并单元格如实上报、图表只计数、误传 docx 拒绝、空演示如实说） |
| `server/app.py` 双端点 `/api/intake/pptx(+/adopt)` | ✅ | API **13 条**（含六意图真链、错误码具名、审核台改意图/风格生效） |
| `docx_adopt.py` source 前缀按格式分流 | ✅ | 随 API 真链断言 |
| `docx_proposal.py` pptx 兜底 deck（更强信号可覆盖） | ✅ | API 断言意图与理由；变异 P4 守护 |
| 审核台同一界面吃 .docx/.pptx（扩展名分流端点与字段） | ✅ | 真浏览器 **1 条**（真上传→提案→改意图→采纳→产物含要点与讲稿） |
| 「布局几何不还原」常驻 limitations 且上屏 | ✅ | 解析断言 ＋ 浏览器断言界面可见；变异 P1 守护 |
| `scripts/mutate_pptx_gates.py` 并入 preflight（第六套） | ✅ | 变异 **4/4 CAUGHT**（P1 几何边界 / P2 回指含形状 / P3 图表只计数 / P4 意图兜底） |

实测过程中被门禁抓到并修掉的真问题：
1. `zipfile.BadZipFile` 不是 `ValueError` 子类，从 `_read` 的异常网里逃逸
   ——改为 stdlib 先验 zip＋检查 `ppt/presentation.xml` 部件，误传 docx
   在门口拒绝而不是在 python-pptx 深处抛 `AttributeError`；
2. python-pptx `merge()` 的语义是起点格拼接被合并格文本，最初断言按
   「原状保留」写反了——解析器如实上报单元格现状是对的，改的是测试；
3. fixture 标题含「路演」会先命中既有 `_DECK_WORDS` 分支，测不到新兜底
   ——换标题专测 pptx 分支。

**顺手修的存量问题**：`docs/ITERATION-v0.8.2-20261020.md` 一处本机绝对
路径让 `test_no_client_material` 在发布后的 main 上是红的（发布时漏网），
已改工作区相对描述。

---

## 二、键盘可达性专项（已完成 · 2026-10-24）

**范围**：C6 迁移后残留的可点元素键盘可达；**只做「键盘可操作」**，读屏器
审计另立版本（PLAN-v0.8 已定边界，未扩权）。

### 交付明细（全部实测）

| 件 | 状态 | 说明 |
|---|---|---|
| 委托层 keydown 激活路径（fox-core.js） | ✅ | 非原生元素（role=button）Enter/Space 派发同一动作表；原生元素（a/button/input…）走原生 click 不重复派发；派发逻辑抽成 `dispatchFoxAction` 单点 |
| Tab 走查门禁（`tests/test_keyboard_walk.py`） | ✅ 5 条 | 两页全部**可见** data-action 控件逐个断言（原生交互 / role=button＋tabindex / aria-hidden 装饰三出路）；Tab 键盘焦点环不被拆；classic 历史项 Enter+Space 真派发；工作台 keydown 路径真派发 |
| classic 历史项 `role="button" tabindex="0"` | ✅ | 唯一非原生动作元素补齐语义 |
| 移动遮罩标 `aria-hidden="true"` | ✅ | 装饰件不当键盘目标；面板开合走带 aria-expanded 的原生按钮 |

### 走查抓到并修掉的两个存量真 bug

1. **classic 五个控件自 v0.7.8 起全灭**：C6 迁移把内联 onclick 改成
   data-action，但 classic 不加载 fox-core.js——没人消费这些标记，只有
   Ctrl+Enter 还能生成。修复：classic 自带最小委托（动作名即本页全局
   函数名，keydown 路径与 fox-core 同构）。
2. **classic 项目历史一直空白**：模板里的 `esc()` 在本页从未定义（定义在
   fox-core.js 里），`loadProjects()` 静默 ReferenceError 被 catch 吞掉。
   修复：本页补 esc 定义。

变异：`mutate_action_delegation_gates.py` 从 4 条扩到 **6 条全 CAUGHT**
（新增 M5 工作台键盘路径被拆、M6 classic 委托被拆），走查门禁并入其
守卫清单。

---

## 三、Tauri 桌面壳 · 两决策点（已拍板 · 2026-10-24 机主定「需要的」）

1. **与 PyInstaller 矩阵的关系：并存。** Tauri 壳＝窗口＋webview＋sidecar
   ＋托盘；PyInstaller 继续作无 Rust 环境的打包兜底——刚验证过的 9 job
   矩阵不动。
2. **Rust 工具链进 CI：壳动工时再加，v0.8.3 不加。** 评估：现有 Test
   矩阵保持轻快（绿标分钟级）；Rust 位会显著拉长流水线并增加维护面，
   与壳的受益不匹配——壳是独立交付物，验收沿用 verify_portable 纪律
   （启动后必须真探测到后端健康端点），动工时随壳一起进 CI。

壳本体按 PLAN-v0.8 的排期属 v0.9 候选；v0.8.3 到此只做决策不做壳代码。

---

## 四、收口清单

- [x] v0.8.2 发版状态核实（10-20 已发，10-24 勘误并本地对齐）
- [x] pptx_import 全量测试跑绿：解析 15 ＋ API 13 ＋ 浏览器 1
- [x] 接线五项完成，接口门禁 + 六意图真链
- [x] 变异 `mutate_pptx_gates` 4/4 CAUGHT 并入 preflight（第六套）
- [x] CHANGELOG `[Unreleased]` 更新（README 版本段落留到发版时配截图）
- [x] 全量回归最终数字：**803 passed / 4 skipped**（2026-10-24 实测，
      含 pptx 全部 29 条新门禁；键盘专项后的最终数字见 CHANGELOG）
- [x] 键盘可达性走查门禁落地（5 条），存量残留清零（classic 委托 + esc）
- [x] Tauri 两决策点拍板：并存；Rust 随壳动工进 CI（2026-10-24 机主定）
- [x] 发版材料就绪：`docs/RELEASE-NOTES-v0.8.3.md` + README/README.en 段落
      ＋ `assets/screenshots/v0.8.3/` 两张实拍（capture_v083_shots.py）；
      版本四处同步（pyproject / `__init__` / uv.lock / 双 README）（机主定节奏）
