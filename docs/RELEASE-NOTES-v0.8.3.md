# v0.8.3 · 贴入 PPT + 键盘可达

**发布日期**：2026-10-25
**主题**：反向拆解再进一格式 —— **一份 .pptx 走 Word 同一条管线**（统一契约 →
提案 → 审核台 → 采纳，零新渲染路径）；**键盘可达性专项**收口整个工作台的
键盘操作，走查门禁顺带抓回两个死了一周的存量 bug。

---

## 一、PPTX 反向拆解：与 Word 同一条管线

上传 .pptx → `pptx_import` 产出统一 `intake_outline` → 既有提案层 → 审核台
（同一张界面，按扩展名分流端点）→ 采纳生成。六个生成器零改动。

| 能拿到的 | 如实说拿不到的（limitations，UI 可见） |
|---|---|
| 页题 → 标题、正文占位符 → 列表（缩进级别保留）、其余文本框 → 段落 | **布局几何不还原**（坐标/母版/主题效果）——常驻每份结果 |
| 表格 → 表格、图片 → 资产候选、讲稿备注 → 正文段落 | 图表与 SmartArt 只计数；合并单元格压成普通行列并上报 |
| evidence＝页号＋形状号（±段落号），100% 可回指 | 外链图片拿不到字节；自造占位符类型降级为普通文本，不崩 |

来源是演示时提案默认按 **deck** 处理（理由随提案可见，更强的信号可覆盖）；
`docx_adopt` 的 source 前缀按格式分流（`pptx:slide-N-shape-M`）。
HTTP 新增 `/api/intake/pptx` 与 `/api/intake/pptx/adopt`。

## 二、键盘可达性专项

- **委托层 keydown 路径**：`role=button` 的非原生元素 Enter/Space 与点击派发
  同一张动作表；原生元素（a/button/input…）走原生 click 不重复派发；
  派发逻辑收敛到 `dispatchFoxAction` 单点。
- **Tab 走查门禁**（真浏览器）：工作台与 classic 两页**全部可见** data-action
  控件逐个断言三条出路之一（原生交互 / role=button＋tabindex / aria-hidden
  装饰）；Tab 焦点环不被拆（v0.8.2 的钴蓝 9.92:1 环在键盘路径上真实可见）；
  classic 历史项 Enter+Space 真派发。
- classic 历史项补 `role="button" tabindex="0"`；移动遮罩标 `aria-hidden`
  （装饰件不进键盘序列，面板开合走带 aria-expanded 的原生按钮）。

### 走查抓回的两个存量真 bug（都修了）

1. **classic 五个控件自 v0.7.8 起全灭**：C6 迁移把内联 onclick 改成
   data-action，但 classic 不加载 fox-core.js——没人消费这些标记，只有
   Ctrl+Enter 幸存。修复：classic 自带最小委托（动作名＝本页全局函数名）。
2. **classic 项目历史一直空白**：模板里的 `esc()` 在本页从未定义，
   `loadProjects()` 的 ReferenceError 被 catch 静默吞掉。修复：本页补定义。

## 三、门禁与证据

| 门禁 | 数字 |
|---|---|
| PPTX 解析合同 | 15 条（含 locator 抽样回读比对、合并单元格、图表只计数、误传 docx 拒绝、空演示如实说） |
| PPTX API | 13 条（错误码具名、审核台改意图/风格生效、六意图真链落盘） |
| 键盘走查 | 5 条（双页控件全覆盖、焦点环、Enter/Space 真派发） |
| 变异 | `mutate_pptx_gates` 4/4 CAUGHT（几何边界常驻 / 回指含形状 / 图表只计数 / 意图兜底），preflight 第六套；委托套件 4→6 条全 CAUGHT（新增键盘路径、classic 委托） |
| 全量 | **808 passed / 4 skipped**（2026-10-25 实测） |

开发中被门禁抓回的真问题：`zipfile.BadZipFile` 逃出异常网（改 stdlib 先验包）、
python-pptx `merge()` 拼接语义与断言预期不符（解析器是对的，改测试）、
fixture 标题含「路演」提前命中旧分支测不到新兜底、v0.8.2 迭代记录一处绝对
路径让卫生门禁在发布后的 main 上红着（已修）。

## 四、Tauri 桌面壳 · 决策记录（本版只决策不动工）

1. **与 PyInstaller 矩阵并存**：壳＝窗口＋webview＋sidecar＋托盘，
   PyInstaller 继续作无 Rust 环境兜底，9 job 打包矩阵不动。
2. **Rust 工具链随壳动工进 CI**，本版不加（保持 Test 矩阵轻快）；
   壳验收沿用 verify_portable 纪律：启动后必须真探测到后端健康端点。

## 五、升级说明

- 无数据迁移：工作区、产物、导出格式、项目数据格式都不变
- 新增可选能力 PPTX 读取复用既有 `[pptx]` extra（导出侧同款）——未装时
  上传 .pptx 会得到明确的 pip 提示，不会静默失败；离线承诺不破
- 键盘行为变化：此前点不动的 classic 控件恢复可用；`role=button` 元素
  现在响应 Enter/Space——如果你的自动化脚本依赖「键盘按了没反应」，
  需要同步更新
