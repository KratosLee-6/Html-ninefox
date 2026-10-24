# v0.8.2 迭代记录 · 界面收敛

**周期**：2026-10-18 ～ 2026-10-20
**目标**：不换主题、不改品牌色，把 Pixel Garden 的**执行层**补齐 —— 面替代线、按钮系统、动效时钟、空态与图标尺度，并让这些尺度可被机器检查。
**结论**：774 passed / 4 skipped；5 套变异全 CAUGHT；`v0.8.2` 已打标签并发布。

---

## 一、五个批次做了什么

| 批次 | 内容 | 产出 |
|---|---|---|
| B2 token 收敛 | 字号下限 10 → 11px；圆角白名单 `{3,4,5,6,999,50%}`；6 个裸 hex 折进 token；`--focus-ring` 独立 | `docs/design-contract.json`、`tests/test_design_contract.py` |
| B3 版面重排 | 面板边界改墨色 10/17/30%；模板缩略图 86 → 128px；检查器空态改为一句话 + 三个入口 | `workbench-system.css`、`fox-core.js`、`index.html` |
| B4 控件纪律 | 按钮 32/36/40 + 五态；图标 16/20、线宽 1.8；像素投影只剩两处 | `tests/test_button_system.py`、`tests/test_v082_surfaces.py` |
| B5 动效 | instant 90 / feedback 140 / enter 180 / panel 200 / exit 140，全 token；禁用 `transition:all` | `motion-system.js`、`tests/test_motion_system.py` |
| B6 手册 | VI 手册 v1.2，补动效、控件、图标、空态四节 | `docs/VI.md` |

## 二、这一版挖到的四个真问题

| 问题 | 根因 | 门禁 |
|---|---|---|
| 导出按钮全变死键 | 编辑检查器模板时把 `openExportCenter` 连带改成 `=> undefined`，静态检查与单测都绿，只有端到端导出用例红 | 动作表出现占位 stub 即红 |
| 夜蓝下模板徽标 1.67:1 | `--surface-raised` **从未定义**，背景透明；`--orange`/`--mono`/`--sans`/`--fw-regular` 同样空引用（警告浮条整条透明） | 任何 `var(--x)` 未定义即红 |
| 首屏仍是旧文案 | 只改了 JS 渲染器，`index.html` 的静态 aside 还写着三行说明 | 空态门禁改为**不点任何东西**就断言 |
| 焦点环 2.87:1 | VI 手册指定陶土橙，但没做对比度验算，低于 WCAG 1.4.11 的 3:1 | 门禁现场算相对亮度，不写死常量 |

## 三、外部交叉评审

MiniMax-M3.1-Flash（`minimax-cn` 通道）评了按钮规范，三条意见本地逐条复算：

- 保留 2px 像素投影，但只用深钴蓝、hover 不放大、active 归零 → 采纳
- 焦点环别用陶土橙 → 采纳（复算 2.87:1，确认它是对的）
- 纯图标按钮补 aria-label / 尺寸 / 间距 → 采纳

记录见 `docs/DESIGN-REVIEW-20261020.md`。

## 四、证据

- 截图 `assets/screenshots/v0.8.2/`：双主题 1440、移动 390、检查器空态、需求面板、审核台、导出中心
- 小红书发布包：工作区 `03_内容/KratosLee小红书/Html九尾狐-界面收敛_2026-10-20/`（仓库外，机主本机）
- 发布说明：`docs/RELEASE-NOTES-v0.8.2.md`

## 五、没有做的（有意）

- 键盘全量导航（Tab 顺序、焦点陷阱、快捷键）→ v0.8.3
- PPTX 导入适配器 → v0.8.3
- 间距 109 处脱网格：记为 burn-down 基线，只禁止变差
- GitHub 历史提交里的旧截图不重写（方案 B：替换 Release 资产）
