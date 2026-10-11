# v0.7.3 发布说明 · 「墨水落纸」动效层

**发布日期**：2026-10-11
**上一版**：v0.7.2（2026-10-09）
**性质**：设计升级。产品 schema、HTTP 接口与项目数据**均未改变**。

---

## 一句话

**六类生成器输出不再是静态截图——共享「墨水落纸」动效层上线，
thesis 来自 Pixel Garden 世界观本身。**

方法论来源：[impeccable](https://github.com/pbakaus/impeccable) 的
animate/audit 纪律（动效必须有从产品概念长出的 thesis；reduced-motion
要保留状态与层级而不是 0.01ms 全杀；导出件是终态文档不是录屏）+
[shaders](https://github.com/shader-effects-inc/shaders) 的材质语言
（氛围渐变、光标辉光——以 CSS 等价实现，零依赖不变，不用 WebGPU）。

---

## Added

| 效果 | 说明 |
|---|---|
| 光带呼吸 | 钴蓝/薄荷径向渐变在纸面上 26s 缓慢漂移（只动 background-position，不触发 layout） |
| 墨水标题 | 首屏 h1 一次性落纸（translateY + blur，700ms focal entrance，cubic-bezier(0.16,1,0.3,1)） |
| 卡片滚动显形 | IntersectionObserver + 同级 stagger（cap 360ms，退场快于入场） |
| 光标辉光 | 仅 `(pointer: fine)`，光标带着薄荷微光——「你的光标在纸上留下光」 |
| 键盘焦点环 | `:focus-visible` 三色描边（a11y 审计缺口补齐） |

三层实现全在 `generators/_shared.py`（六类渲染器共享，单文件输出依旧零依赖）。

## 三条「终态」通路——内容永不可见不算完成

1. **prefers-reduced-motion**：全部元素静态呈现（不是 0.01ms 全杀——
   状态变化与层级完整保留，impeccable 审计对 motion sensitivity 的要求）；
2. **@media print**：浏览器原生打印同样定格；
3. **导出定格 `_settle_ambient()`**：`exporting.py` 的 PNG 与 PDF 两条
   路径在捕获前把 reveal 元素置为可见、冻结光带、移除辉光——否则全页
   导出的视口外卡片会留在 opacity:0 空白（本轮设计评审特别防的缺陷）。

JS 侧另有 1.8s 超时兜底：任何环境下未显形的元素直接以终态呈现。

---

## 门禁

| 新增 | 反向验证 |
|---|---|
| `tests/test_ambient_motion.py`（15 条）：六类输出动效资产齐全（结构层）；reduced-motion 块归静态；导出与验收脚本定格 | `scripts/mutate_ambient_motion_gates.py`：撤动效层 / 删 reduced-motion / 导出不定格 → **3/3 CAUGHT** |
| 浏览器 e2e | **22/22** |
| 视觉验收 | 六类产物 **6/6 pass**（光带可感知不喧宾、无 opacity 空白、原版式完整） |
| 全量回归（Windows 本机） | **631 passed / 2 skipped**（68 个测试文件；本轮新增 15 条；Linux CI 预期 632 passed / 1 skipped） |
| 发布元数据 | `check_release_version.py`：v0.7.3 四处一致 |

---

## 明确不在这一版

- 工作台界面的动效（已有 motion-system 体系，本轮只动生成器输出面）；
- WebGPU/着色器材质（保持零依赖；shaders 的语言已用 CSS 等价 borrowed）；
- 生成页的 parallax / 长滚动编排（impeccable：不为存在而动画）。
