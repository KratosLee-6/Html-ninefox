# 🦊 Html九尾狐 v0.3.0 · Skill Alliance 3 PPT Skills

> 🎉 **v0.3.0 = v0.3.0b2 + 3 飞书绝活大会 PPT 技能集成**

**Released**: 2026-09-03 · **Tag**: `v0.3.0` · **Commit**: `73ef786` (main)

---

## ✨ What's New

### 3 PPT Skills Integrated (from 飞书绝活大会)

| Skill | Author | Style |
|---|---|---|
| [baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck) | [宝玉 (JimLiu)](https://github.com/JimLiu) | AI 画图生成每页 · 17 套风格 |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) | [张咋啦 (zarazhangrui)](https://github.com/zarazhangrui) | 3 版首页 · 避开 AI 紫渐变 |
| [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates) | [张咋啦](https://github.com/zarazhangrui) | 28 套稳定 · 字体配色不动 |

### 🔧 5-Class Intent Router (generate_expert)

- `landing` (existing) → local template
- `ppt_image` (new) → baoyu-slide-deck manifest
- `ppt_html` (new) → frontend-slides manifest
- `html_template` (new) → beautiful-html-templates manifest
- `infographic` (existing) → huashu-design manifest

### 🙏 Acknowledgments Expanded

- 🎨 **[宝玉 (JimLiu)](https://github.com/JimLiu)** — baoyu-skills
- 🎨 **[张咋啦 (zarazhangrui)](https://github.com/zarazhangrui)** — frontend-slides / beautiful-html-templates / beautiful-feishu-whiteboard
- (继承 v0.2 起：歸藏 / 花叔 / tt-a1i)

---

## ✅ Tests · All Passing

- 4/4 integration tests
- 146/146 pytest
- 20/20 Chromium E2E
- 12/12 security tests (P0 shell injection fixed)

---

## 📦 Downloads (继承 v0.3.0b2 资产)

| Platform | File | Size |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.3.0.exe` | installer |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.3.0.zip` | portable |
| Linux | `HtmlNineFox-Linux-0.3.0.run` | installer |
| Linux | `HtmlNineFox-Linux-0.3.0.tar.gz` | portable |
| Python 3.10+ | `htmlninefox-0.3.0-py3-none-any.whl` | wheel |

> v0.3.0 release 暂复用 v0.3.0b2 资产；下次 CI 重新构建 v0.3.0 品牌包。

---

## 🚀 Quick Start

```bash
# From source
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox
uv sync
uv run htmlninefox app
```

```bash
# From wheel
pip install htmlninefox-0.3.0-py3-none-any.whl
htmlninefox app
```

```bash
# Generate HTML (CLI)
htmlninefox expert "做一个 AI 工具发布会 PPT" --template ppt_image
```

---

## 📚 Documentation

- [README](https://github.com/KratosLee-6/Html-ninefox#readme)
- [CHANGELOG](https://github.com/KratosLee-6/Html-ninefox/blob/main/CHANGELOG.md)
- [docs/INSTALL.md](https://github.com/KratosLee-6/Html-ninefox/blob/main/docs/INSTALL.md)
- [docs/ROADMAP.md](https://github.com/KratosLee-6/Html-ninefox/blob/main/docs/ROADMAP.md)

---

## 🌟 Inspiration

飞书绝活大会原话：「有了 Skill，不代表一句话就能得到好作品。真正拉开差距的，是**清晰的 Brief、可复用的审美模板，以及一轮轮具体反馈**。」

Html九尾狐 v0.3.0 把这句话做成了可执行的 CLI。

---

Made with 🦊 by [KratosLee](https://github.com/KratosLee-6) · [MIT](LICENSE)