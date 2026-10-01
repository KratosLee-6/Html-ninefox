# Assets · 主仓库视觉资产

本目录保存 README、发布说明、测试证据和产品演示使用的视觉资产。截图必须来自真实可运行页面或可复现的自动化状态，不能用与产品无关的概念图替代功能证据。

## 当前结构

```text
assets/
├── README.md
├── promo/                            # 40s 品牌宣传片（中英双版）
│   ├── htmlninefox-brand-film-40s-16x9.mp4
│   ├── htmlninefox-brand-film-40s-16x9-en.mp4
│   ├── poster-zh.png                 # README 可点击封面（GitHub 不渲染 <video>）
│   └── poster-en.png
├── screenshots/
│   ├── README.md
│   ├── v0.3.0b2/ ... v0.5.0rc3/   # 已发布或历史版本快照
│   └── v0.5.0rc3-visual/           # 2026-09-24 main 视觉收敛证据
├── 动态演示.gif
├── 演示1.jpg
├── 演示2.jpg
├── 演示3.jpg
├── cli-demo-interactive.html
└── generate-screenshots.py
```

`assets/screenshots/v0.5.0rc3-visual/` 当前包含 14 张截图，覆盖 Paper / Pixel Night、桌面 / 平板 / 手机、命令面板、Project Memory、生成结果、Export Center、受控错误和 Revision Restore 等真实产品状态。

`assets/promo/` 是 40 秒品牌宣传片的中英双版（1920×1080 / 25fps / H.264 / 无声）。**片中已不含任何生成式镜头**：所有产品界面画面全部取自本目录 `v0.6.0/` 的真实运行截图，不使用概念图替代功能证据；开场标题卡、标语卡、版本沿革卡与尾卡是由脚本用 Playwright 渲染的静态卡，其中品牌标志直接渲染自 `htmlninefox/server/static/logo-mark.svg` 官方源文件。

> 取景说明：截图为 16:10，片子是 16:9。脚本用 `scale=...:force_original_aspect_ratio=decrease` + `pad` **留边而非裁切**，所以顶栏一直可见——`v0.6.0` 版本徽标在每个界面镜头里都能读到。此前版本用 `crop`，把顶栏裁掉了，徽标只在每个镜头开头约 1 秒偶然可见。
>
> 另有一处已修的取景缺陷：`zoompan` 的 `x = (iw - iw/zoom) * cx` 在 `zoom=1` 时恒为 0，也就是从**左上角**取景；旧参数从 1.0 起zoom，每个镜头都从角落往中间漂。现改为 1.06 → 1.00，居中且从稳定状态起幅。

**镜头与功能一一对应**：12 个界面镜头 ↔ 12 项可截图验证的功能，映射表是脚本内的 `CATALOGUE`，`validate_script()` 会在「有功能没镜头」或「有镜头没登记」时直接报错退出。没有本轮实拍的能力（LLM 接入、离线引擎、Project Memory、命令面板、版本历史、生成取消、六类产物等）**不出现片中**，逐条原因列在 `NOT_IN_FILM`——片中不出现，比拿旧版截图凑数更诚实。

**版本沿革卡**的数据取自 `docs/ROADMAP.md` 的版本历史表，跨语言一致。

重渲命令（需要 `ffmpeg` + `ffprobe` 与 Playwright chromium）：

```bash
python scripts/make_promo_film.py
```

该脚本对每个片段与最终成片做时长校验，不符即中止且**不覆盖**仓库中已有文件。片长由 `SCRIPT` 表推导（`film_seconds()`）而非写死——写死过一次，结果文件名写成 `60s` 而实际 40s。

GitHub 的 Markdown 清洗器不支持 `<video>` 标签，因此主 README 用 `[![封面](poster.png)](raw 链接)` 形式跳转播放，不要改回内嵌 `<video>`。

## 使用规则

- 按版本或明确的开发切片建立目录，例如 `v0.5.0rc3/`、`v0.5.0rc3-visual/`。
- 文件名使用小写英文和连字符；响应式截图在名称中写入 viewport 宽度，例如 `workbench-mobile-390.png`。
- README 主视觉优先采用当前 `main` 的稳定、可复现工作台状态；发布说明仍引用对应 tag 的历史截图。
- 成功、错误、恢复、空状态等截图必须由真实操作触发，并能由测试或记录说明复现方式。
- 不覆盖旧版本截图。产品变化时创建新目录，保留历史证据。
- 外部参考图、未确认许可的素材和用户私密内容不得提交到仓库。

## RC3 证据入口

- [RC3 截图清单](screenshots/README.md)
- [RC3 视觉收敛记录](../docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)
- [Pixel Garden UI 指南](../docs/UI-GUIDE.md)
- [可复现状态测试](../tests/test_rc3_visual_evidence_states.py)

生成或更新截图后，应检查图片可读性、对应文档链接和 Git diff，并运行与状态相关的浏览器测试。
