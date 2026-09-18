# Html九尾狐 v0.5.0rc2

`v0.5.0rc2` 把 RC1 的 Project Memory 与本轮版本历史、恢复、原生动效、无障碍和 100 节点验收合并为可安装的应用预发布版。它适合希望试用最新工作台闭环并反馈真实问题的用户；`v0.4.2` 继续作为稳定版。

## 主要变化

- 每次反馈修改、重新生成和历史恢复都会保留 HTML 与生成状态快照。
- 版本历史支持命名、源码差异、父版本、恢复来源，以及“恢复为新版本”；不会覆盖旧稿。
- 过期恢复返回版本冲突，写入采用临时文件与原子替换；校验或写入失败时保留当前产物。
- 兼容早期只有 HTML 的历史记录，并明确标记无法完整恢复的版本。
- 工作台加入“系统 / 减少动效 / 关闭动效”三档偏好、可取消动画、并发预算、离屏跳过和重试竞态清理。
- 生成与局部重跑使用稳定阶段提示，最多同时显示 4 条 Toast；`/motion-lab` 提供六类本地样例。
- 浏览器验收覆盖弹窗 Tab 循环、Escape 关闭与焦点返回、390px 手机布局，以及 100 节点 / 99 连线的渲染、框选、移动和保存。

## 下载

- Windows 安装器：`HtmlNineFox-Setup-0.5.0rc2.exe`
- Windows 便携包：`HtmlNineFox-Windows-x64-0.5.0rc2.zip`
- Linux 自解压安装包：`HtmlNineFox-Linux-0.5.0rc2.run`
- Linux 可审计归档：`HtmlNineFox-Linux-0.5.0rc2.tar.gz`
- Python wheel：`htmlninefox-0.5.0rc2-py3-none-any.whl`
- 每个文件旁均提供 `.sha256.txt` 校验文件。

Docker 镜像在标签 CI 中从源码构建并验证 Chromium 导出运行时，但本次不上传公共镜像仓库。Docker 用户请从源码执行 `docker compose up --build`。

## 实测界面

![v0.5.0rc2 纸白工作台](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc2/assets/screenshots/v0.5.0rc2/workbench-overview.png)

当前版本的纸白工作台截图由 22 项 Chromium 发布验收生成；Release 同时附带夜蓝工作台和导出中心原图。

![版本历史、源码差异与恢复](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc2/docs/test-evidence/motion-20260918/revision-history-desktop.png)

版本历史弹窗显示版本名称、父版本与恢复来源，可比较源码并把旧稿恢复为新版本。

![原生动效实验室](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc2/docs/test-evidence/motion-20260918/motion-lab-desktop.png)

动效实验室覆盖操作反馈、选中素材、建立连接、阶段切换、产物就绪和版本恢复，并响应系统 / 减少 / 关闭三档偏好。

![v0.5.0rc2 导出中心](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.5.0rc2/assets/screenshots/v0.5.0rc2/export-center.png)

导出中心实测 PNG 逐页导出，兼容性 100 分；弹窗内保留文件与 `export-report.json` 下载入口。

## DeepSeek Harness 插件

DSH 插件继续使用独立版本 [`dsh-htmlninefox@0.1.0-preview.1`](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)。应用安装包不包含 Harness，插件包也不等同于应用安装包。npm 发布暂缓，当前验证渠道是插件 Release 中的 tarball。

## 验证范围

发布前运行版本元数据、内联与独立 JavaScript、完整 pytest、Chromium 端到端、DSH 插件测试、wheel 隔离安装、真实 PNG 导出和 Windows 便携包启动冒烟。标签流水线另外重建 Windows / Linux 包、生成 SHA-256，并验证 Docker 导出运行时。结果与命令见 [发布测试报告](TEST-REPORT-v0.5.0rc2.md)。

## 已知限制

- 未完成 Safari、iOS 和 WebView2 实机验收。
- 同一服务进程内有写入锁和版本冲突保护；多进程同时编辑及突然断电后的跨文件事务恢复仍未保证。
- 100 节点验收是操作耗时门禁，不代表所有设备稳定达到 60fps，也不覆盖 100 个动态 iframe。
- DSH 尚未用付费真实模型验证“对话中自主选择技能”，首版也没有专用工具卡片或聊天内 HTML 预览。
- Windows 安装器未代码签名，可能触发 SmartScreen 提示。

问题与反馈请提交到 [GitHub Issues](https://github.com/KratosLee-6/Html-ninefox/issues)，附上系统、安装包名称、复现步骤和脱敏日志。
