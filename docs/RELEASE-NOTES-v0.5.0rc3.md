# Html九尾狐 v0.5.0rc3

`v0.5.0rc3` 将 2026-09-24 的 RC3 Pixel Garden 视觉与交互收敛打包为可安装预发布版。稳定版仍为 `v0.4.2`；DeepSeek Harness 插件继续使用独立版本 `0.1.0-preview.1`。

## 主要变化

- 重构工作台顶栏，突出“输入需求”和“推进工作区”两条主路径，次要工具收进 More 菜单。
- 建立桌面、窄桌面、平板和手机四档布局；手机使用可阅读的任务视图，不再缩小整张无限画布。
- 节点支持 overview、compact、detail 三档语义缩放。
- 按钮、输入框、节点、检查器、弹窗和命令面板统一 focus、selected、disabled、busy、success、error 与 reduced-motion 状态。
- 使用仓库内 SVG Icon，经典表单模式与工作台共享 Pixel Garden 纸白、钴蓝、薄荷和陶土品牌系统。
- Project Memory、Export Center、命令搜索、受控导出错误和 Revision Restore 完成状态均有真实页面与可复现截图证据。
- 修复 RC3 CSS 未进入 wheel 资源清单的问题，安装包现在包含 `pixel-garden-tokens.css` 与 `workbench-system.css`。

## 下载

- Windows 安装器：`HtmlNineFox-Setup-0.5.0rc3.exe`
- Windows 便携包：`HtmlNineFox-Windows-x64-0.5.0rc3.zip`
- Linux 自解压安装包：`HtmlNineFox-Linux-0.5.0rc3.run`
- Linux 可审计归档：`HtmlNineFox-Linux-0.5.0rc3.tar.gz`
- Python wheel：`htmlninefox-0.5.0rc3-py3-none-any.whl`
- 每个应用包附带 `.sha256.txt`。

## 实测界面

![RC3 纸白工作台](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc3/assets/screenshots/v0.5.0rc3-visual/workbench-paper-1440.png)

![RC3 手机任务视图](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc3/assets/screenshots/v0.5.0rc3-visual/workbench-mobile-390.png)

![Project Memory 保存完成](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc3/assets/screenshots/v0.5.0rc3-visual/project-memory-saved.png)

![Revision Restore 完成](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc3/assets/screenshots/v0.5.0rc3-visual/revision-restore-complete.png)

Release 附带 3 张由 Chromium 22 项验收生成的 1440×900 工作台截图；另外 14 张响应式与业务状态证据保留在仓库的 `assets/screenshots/v0.5.0rc3-visual/`。

## 验证

发布候选通过完整 pytest、Chromium E2E、JavaScript 语法、DSH 插件测试、版本一致性以及 wheel 隔离安装和静态资源审计。Windows、Linux、SHA-256 与 Docker Chromium 由标签工作流在对应环境重新构建验证。详见[发布测试报告](https://github.com/KratosLee-6/Html-ninefox/blob/main/docs/TEST-REPORT-v0.5.0rc3.md)。

## 已知限制

- 尚未完成 Safari、iOS 和 WebView2 实机验收。
- 多进程同时编辑及突然断电后的跨文件事务恢复仍在 RC3-D 计划中。
- Windows 安装器未代码签名，可能触发 SmartScreen 提示。
- DSH 插件不会随应用包自动安装或升级。

问题与反馈请提交到 [GitHub Issues](https://github.com/KratosLee-6/Html-ninefox/issues)，附上系统、安装包名称、复现步骤和脱敏日志。
