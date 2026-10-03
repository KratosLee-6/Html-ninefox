# Assets · 主仓库视觉资产

本目录保存 README、发布说明、测试证据和产品演示使用的视觉资产。截图必须来自真实可运行页面或可复现的自动化状态，不能用与产品无关的概念图替代功能证据。

## 当前结构

```text
assets/
├── README.md
├── promo/                            # 品牌宣传片
│   ├── htmlninefox-brand-demo-50s-16x9.mp4    # 50s 真实操作录屏（定稿 · 中文）
│   ├── htmlninefox-brand-demo-53s-16x9-en.mp4 # 53s 真实操作录屏（定稿 · English）
│   ├── poster-demo-zh.png                    # 50s 成片抽帧（中文 README 展示位）
│   ├── poster-demo-en.png                    # 53s 成片抽帧（English README 展示位）
│   ├── htmlninefox-brand-film-34s-16x9.mp4    # 34s 静帧速览（中英双版 · 备选）
│   ├── htmlninefox-brand-film-34s-16x9-en.mp4
│   ├── opener-h3-2k.mp4              # 开场抽象氛围镜头（MiniMax-H3 生成 · 8s 2K）
│   ├── brand-bed.mp3                 # 全片器乐床（67s 无人声）
│   └── poster-zh.png / poster-en.png # 34s 版封面
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

`assets/promo/` 里有两支片子，**用途不同，不要混淆**：

- **50s 中文 / 53s English 真实操作录屏（定稿）**
  `htmlninefox-brand-demo-50s-16x9.mp4` / `htmlninefox-brand-demo-53s-16x9-en.mp4`
  由 `scripts/record_demo_film.py` 驱动 **v0.6.0 的真实运行服务**录下：
  光标真的移动、需求真的逐字打出、节点真的逐个长出、导出中心真的被点开。
  字幕里的每个数字都是产品当场报出的（中文版置信度 67%、英文版 72%——
  因为英文版是**独立录制**，英文需求被重新分析过，两者之间不共用数字；
  分析耗时 8ms、交付 40ms、兼容性 100、「未发现阻塞性兼容问题」）。
  **界面在两版里都是中文**：工作台默认中文，这是产品事实；分析返回的
  chips（落地页 / 首页 Hero）是产品自己的输出，同样不改写。
- **34s 静帧速览（备选，中英双版）**
  23 张真实截图交叉淡入，用于无录屏环境或静态渠道；它是**速度概览**而非演示。

**为什么界面不用 H3 生成**：文生视频模型会把中文渲染成乱码、按钮位置随机、
连线毫无逻辑、点击无反应——那与「可正常演示」直接矛盾。唯一由 H3 生成的是
**开场 3.5s 抽象氛围**，提示词明确禁止任何文字。34s 静帧版另有自己的说明，
其取景、字幕与音效细节见下文。

**声音**：全片有一条器乐床 `brand-bed.mp3`（无人声，音量 0.16，2 秒淡入 / 2.2 秒淡出，末端 `alimiter=0.92` 防削顶）。开场的 H3 原生环境音保留并在 0.4s 交叉淡入处淡出，随后由器乐床接管。实测成片 `mean_volume -28.7 dB` / `max_volume -10.0 dB`。

> 早期版本是静音的，拼接时用 `-an` 丢弃 H3 音轨；被反馈「没有声音，不是很舒服」后改为上图的混音。

> 取景说明：截图为 16:10，片子是 16:9。脚本用 `scale=...:force_original_aspect_ratio=decrease` + `pad` **留边而非裁切**，所以顶栏一直可见——`v0.6.0` 版本徽标在每个界面镜头里都能读到。
>
> **界面镜头一律静态**。早先版本给每个镜头加了 Ken Burns 缓慢缩放，实际观感是「一直在抖」，被明确指为不舒服；现在 `kenburns()` 只保留 `scale` + `pad`，运动只留给 H3 开场。UI 截图不需要运镜，静态帧 + 交叉淡入更像产品本身而不是预告片。

**镜头是精选子集，不是功能全覆盖**：10 个界面镜头（+ 标题卡 / 尾卡）↔ `CATALOGUE` 21 项真实功能中的 10 项，映射表在脚本内，`validate_script()` 强制校验「每个镜头都对应清单里存在的功能」+「镜头数不低于 8」+「同一功能不重复出镜」。

> 早先的规则是**每个功能都必须有镜头**，那等于片子必须覆盖全部 21 项，63s / 21 镜由此而来，并被反馈为「太长、画面一直在抖、前面十几秒看不到产品」。这条规则本身就是长度的来源，已改为精选子集 + 数量下限。清单里未入选的 11 项由 README 与 23 张截图集承担说明，逐条原因列在脚本的 `NOT_IN_FILM`；片中不出现，比拿旧版截图凑数更诚实。

**版本沿革卡**的数据取自 `docs/ROADMAP.md` 的版本历史表，跨语言一致。

重渲命令（需要 `ffmpeg` + `ffprobe` 与 Playwright chromium）：

```bash
python scripts/make_promo_film.py
```

该脚本对每个片段与最终成片做时长校验，不符即中止且**不覆盖**仓库中已有文件。片长由 `SCRIPT` 表推导（`film_seconds()`）而非写死，且**必须是整秒**——脚本会在片长非整数时直接报错退出。写死过一次（文件名写 `60s` 而实际 40s），改成推导后又出现过一次（片长 54.5s 而 `round()` 得到 54，文件名比成片短半秒），因此现在宁可用整秒凑，也不让文件名去四舍五入。

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
