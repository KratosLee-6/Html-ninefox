# 按钮系统交叉评审 · MiniMax-M3.1-Flash（2026-10-20）

**评审方式**：把 v0.8.2 的按钮规范整理成一段约束，走 `minimax-cn` 通道
（`api.minimaxi.com/anthropic`，模型 `MiniMax-M3.1-Flash`）请它只回答三个问题。
**本地复核**：它的结论我们逐条用相对亮度公式复算过，不盲信。

> 调用细节：该模型强制 adaptive thinking，`max_tokens` 需给足（实测 9000 才
> 有正文），否则 token 全花在思考里、`content` 为空。这是踩过的坑。

---

## 它的三条意见

| # | 意见 | 本地复核 | 采纳 |
|---|---|---|---|
| 1 | 2px 硬投影**保留**，只给 primary；用更深的钴蓝、hover 不放大、active 下移归零 | 与 VI「少量像素识别」一致 | ✅ 采纳，投影色改为 `accent 62% + text-primary` 的深钴蓝 |
| 2 | 焦点环**别用陶土橙**，对比不足；改钴蓝 | 复算：陶土橙对暖纸白 **2.87:1**（它说 2.42）、对纸白 2.57:1，均低于 WCAG 1.4.11 的 3:1；钴蓝 **9.92:1 / 8.88:1** | ✅ 采纳，新增 `--focus-ring`（浅色钴蓝、夜蓝 `#9BC0FF`），`--focus` 只留给选区与装饰 |
| 3 | 纯图标按钮需要：`aria-label` 必填、tooltip 同名、桌面 ≥32×32、移动 ≥40、间距 ≥8、状态不改尺寸 | 我们此前没有明文规范 | ✅ 采纳，落 CSS 与门禁 |

---

## 落地的改动

- `--focus-ring`：浅色 `#173C8F`、夜蓝 `#9BC0FF`；所有 `:focus-visible` 与弹窗输入框改用它
- primary 投影：`2px 2px 0 color-mix(--accent 62%, --text-primary)`；hover 不位移不放大；active 位移 2px 且投影归零
- `.btn-icon`：32×32（移动 40），点击区与图标都居中
- 门禁：`test_focus_ring_meets_non_text_contrast`（跑相对亮度，≥3:1）、
  `test_icon_only_buttons_are_labeled_and_sized`（可访问名 + 尺寸）

## 没采纳 / 待定

- 它建议 hover 完全不变化：我们仍保留「面变亮」，因为像素风下投影不动、需要另一条
  hover 反馈（颜色变化对色觉障碍更友好）。理由留档，后续可在真机上对比。
