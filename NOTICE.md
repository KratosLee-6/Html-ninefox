# NOTICE · 署名、引用与第三方组件

> 本文件是 `LICENSE`（MIT）的补充说明，**不改变、不收紧 MIT 授予你的任何权利**。
> 它做三件事：说明怎么署名、给出引用格式、把第三方来源与许可边界写清。

---

## 1. 版权与许可

- 代码与文档：**MIT**，见 [LICENSE](LICENSE)。
- 版权人：`KratosLee · Html九尾狐项目组`，2026。
- MIT 允许商用、修改、再分发、闭源集成——只要在副本或实质性部分中**保留版权声明与许可声明**。

## 2. 怎么署名（分发与集成时）

在下列任一处保留即可，位置由你决定：

- 产品「关于 / About」页；或
- 随附的 `LICENSE` / `NOTICE` 文件；或
- 应用内的第三方组件清单。

最小署名行（可直接复制）：

```text
Html九尾狐 (HtmlNineFox) © 2026 KratosLee · MIT License
https://github.com/KratosLee-6/Html-ninefox
```

**衍生作品建议**（请求，非强制）：保留本 `NOTICE.md`，并在说明里写清你改了什么。这不是 MIT 之外的附加条件，只是让下游能追溯。

## 3. 引用格式（文章 / 教程 / 论文 / 课程）

机器可读版本见 [CITATION.cff](CITATION.cff)（GitHub 侧边栏会显示「Cite this repository」）。

中文：

```text
KratosLee. (2026). Html九尾狐：人机共驾的 HTML 内容交付工作台（v0.8.0）[计算机软件].
https://github.com/KratosLee-6/Html-ninefox
```

English:

```text
KratosLee. (2026). HtmlNineFox: a human-in-the-loop HTML delivery workbench (v0.8.0) [Computer software].
https://github.com/KratosLee-6/Html-ninefox
```

引用时请带上**版本号**——本项目每个小版本都改界面与导出矩阵，不带版本号的引用很快会失真。

## 4. 名称、标识与品牌视觉不在 MIT 范围

MIT 覆盖的是**代码与文档**。以下保留权利，避免被误认为官方出品：

- 名称「Html九尾狐 / HtmlNineFox」及其 Logo（`server/static/logo-*.svg`、`icon.svg`）；
- 「Pixel Garden / 像素花园」视觉系统与品牌色板；
- 项目的发布渠道与 Release 签名。

你可以说「基于 Html九尾狐构建」，但不要暗示获得官方背书，也不要把改版产品继续叫「Html九尾狐官方版」。

## 5. 第三方组件与来源

| 组件 / 来源 | 许可 | 用途 | 我们的处理 |
|---|---|---|---|
| [python-pptx](https://github.com/scanny/python-pptx) | MIT | `.pptx` 服务端受控映射 | 依赖，未改源码 |
| [python-docx](https://github.com/python-openxml/python-docx) | MIT | `.docx` 语义导出（v0.8 起） | 可选 extra `[docx]` |
| [Univer](https://github.com/dream-num/univer)（dream-num） | Apache-2.0 | 工作台内幻灯片可视化编辑 | 前端依赖；Apache-2.0 的 NOTICE 要求由该库自身满足 |
| [Archify](https://github.com/tt-a1i/archify) | MIT | 架构图生成（README 与 `docs/diagrams/`） | 产出图随仓库发布 |
| [huashu-design](https://github.com/alchaincyf/huashu-design)（花叔） | MIT | 设计方法与评审流程参考；v3.0 起有 20 条设计哲学 | **方法参考**，模板为 clean-room 原生实现 |
| [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) | MIT | 解说视频动画引擎（`film/v070-huashu/`） | 按 MIT 使用 |
| [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill)（归藏） | **AGPL-3.0** | 电子杂志 × 电子墨水的版式方法论 | **仅方法借鉴，不复制代码/模板/资产**；详见 `docs/DESIGN-SOURCES.md` |
| [guizang-product-video-skill](https://github.com/op7418/guizang-product-video-skill) | **AGPL-3.0** | 宣传片工程方法论；`film/sfx` 音效 | 音效为其原创合成，附使用声明；不复制代码 |
| [baoyu-skills](https://github.com/JimLiu/baoyu-skills)（宝玉） | MIT | 「AI 画图生成每页 PPT」方法参考 | 方法参考，本地 fallback 自研 |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) / [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates)（张咋啦） | MIT | 「避开 AI 紫渐变、稳定出片」设计哲学 | 方法参考；如整条引入模板需保留其版权声明 |
| [edge-tts](https://github.com/rany2/edge-tts) | 自定义（非标准开源许可） | 解说视频人声合成 | **仅用于制作发布物料，不进入软件运行链路** |

### AGPL 边界（重要）

`guizang-ppt-skill` 的 GitHub 许可为 **AGPL-3.0**，本项目**不分发、不 vendor 其任何代码、模板或资产**：

- 仓库内 `templates/gallery/guizang-*.html` 与 `preset_id: guizang-magazine` 是**clean-room 原创实现**，方法层面参考公开的编辑设计原则（见 `docs/DESIGN-SOURCES.md` 的审计记录）；
- 若下游要直接使用归藏的原版模板，请自行获取并遵守 AGPL-3.0；
- 命名保留 `guizang-` 前缀是为了标明**灵感来源**，不是版权归属声明。若这一命名引起误解，后续会改为 `fox-ink-*` 之类的中性名（见 `docs/PLAN-TEMPLATE-EXPANSION.md`）。

## 6. 分发前自检（4 条）

- [ ] 副本里有 `LICENSE`（MIT 全文）
- [ ] 副本里有本 `NOTICE.md`，或等价的署名清单
- [ ] 你的改版没有继续使用「Html九尾狐官方」字样
- [ ] 若集成了上表中的第三方代码，各自的许可声明仍在

---

有署名或授权方面的疑问，走 GitHub Issue，或见 [CONTRIBUTING.md](CONTRIBUTING.md)。
