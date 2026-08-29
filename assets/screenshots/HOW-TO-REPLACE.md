# Html九尾狐 · 截图替换指南

> 状态：**6 张 PNG 已生成**（2026-08-29 17:36）
> 总大小：**~643 KB**（每张 76-125 KB）

---

## 🎉 6 张图全部就绪

| # | 文件 | 尺寸 | 大小 | 用途 |
|---|---|---|---|---|
| 1 | `hero.png` | 1600×900 | 76 KB | README 顶部主视觉 |
| 2 | `cli-demo.png` | 1200×800 | 120 KB | 终端 CLI 跑通截图（stage 3）|
| 3 | `5-style-compare.png` | 1600×900 | 118 KB | 4 风格候选实时评分 |
| 4 | `workbench.png` | 1440×900 | 82 KB | 工作台 5 板块界面 |
| 5 | `sequence-diagram.png` | 1600×1000 | 122 KB | 5 智能体协作时序图 |
| 6 | `output-example.png` | 1440×900 | 125 KB | Linear 风格落地页实际产物 |

---

## 🚀 一键验证（1 分钟）

```bash
# 1. 打开 README 看效果
open "E:\工作\【汐构科技】\客户跟进\Html九尾狐\07_GitHub开源发布\README.md"

# 2. 在文件浏览器看 6 张图
explorer "E:\工作\【汐构科技】\客户跟进\Html九尾狐\07_GitHub开源发布\assets\screenshots"
```

**验收清单**：
- [ ] `hero.png` 标题清晰，xterm.js 终端可见
- [ ] `cli-demo.png` 看到 5 智能体 pipeline 进度
- [ ] `5-style-compare.png` 右侧 4 张风格卡片高亮
- [ ] `workbench.png` 5 大板块（顶部 + 左侧 + 中部 + 右侧 + 底部）|
- [ ] `sequence-diagram.png` 7 participants 时序清晰
- [ ] `output-example.png` Linear 风格 SaaS 落地页

---

## 🔄 如果某张图需要重新生成

```bash
# 重新跑脚本（覆盖所有 6 张）
cd "E:/工作/【汐构科技】/客户跟进/Html九尾狐/07_GitHub开源发布"
C:/Users/Admin/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe assets/generate-screenshots.py

# 跑完看输出：
#   ✓ hero.png                1600x900 (76 KB)
#   ✓ cli-demo.png            1200x800 (120 KB)
#   ...
```

**单张重截**（修改 `generate-screenshots.py` 后只留 1 个 TARGET 即可，~10 秒）。

---

## 🛠️ 替换 README 占位（可选 · 已生成的图已经是真实图）

README.md 中原本有 6 处 `<!-- TODO [KX]: -->` 占位——如果你想用实际图片替换文字占位，可以这样做：

### 方式 A · 用 markdown 图片引用（推荐 · 简单）
找到 `README.md` 中形如：
```html
<!-- TODO [KX]: replace placeholder images after running expert CLI on real use cases -->
<p align="center">
  <img src="assets/screenshots/hero.png" alt="..." width="800" />
</p>
```
**保留不动**——已经是正确路径了（GitHub 会自动渲染 PNG）。

### 方式 B · 用 sed 去掉占位注释（清理）
```bash
cd "E:/工作/【汐构科技】/客户跟进/Html九尾狐/07_GitHub开源发布"

# macOS / Linux
sed -i '' '/TODO \[KX\]:/d' README.md

# Windows PowerShell
(Get-Content README.md) | Where-Object { $_ -notmatch 'TODO \[KX\]:' } | Set-Content README.md
```

---

## 📋 主人下一步 3 件事

1. **看 6 张图**（1 分钟验证）
2. **清理 README 占位**（如果想干净 → 方式 B · 30 秒）
3. **git add + commit + push**（5 分钟上线）
   ```bash
   cd "E:/工作/【汐构科技】/客户跟进/Html九尾狐/07_GitHub开源发布"
   git init
   git add .
   git commit -m "feat: v0.2.0 GitHub release with 6 screenshots"
   git remote add origin https://github.com/YOUR_USER/htmlninefox.git
   git push -u origin main
   ```

---

## 🐛 已知 limitation

1. **`5-style-compare.png` 是手动在 style_expert 阶段截的**（8 秒后），如果未来 xterm.js 脚本调整时间线，需要重新生成
2. **`output-example.png` 来自 `C:/tmp/day10c/`**——如果该目录被清理，generate-screenshots.py 会失败 → **先跑 `python -m htmlninefox expert` 重新生成产物**
3. **PNG 文件是按截图时序生成的**——xterm.js 字符位置不同时刻会略有差异

---

> 截图生成时间：2026-08-29 17:36
> 脚本版本：v0.1（generate-screenshots.py）
> 总产出：6 张 PNG · ~643 KB · 适合直接嵌入 GitHub README
