# Assets · 主仓库视觉资产

本目录保存 README、发布说明、测试证据和产品演示使用的视觉资产。截图必须来自真实可运行页面或可复现的自动化状态，不能用与产品无关的概念图替代功能证据。

## 当前结构

```text
assets/
├── README.md
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
