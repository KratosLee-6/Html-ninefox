# RC2 迭代记录 · 版本历史、恢复与验收

日期：2026-09-18。功能开发始于 `0.5.0rc1`，完成验收后已提升应用版本为 `0.5.0rc2`，并纳入应用预发布标签与安装包流水线。

## 发布追记

- 应用预发布：[v0.5.0rc2](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc2)。
- Windows 安装器 / 便携包、Linux `.run` / `.tar.gz`、Python wheel 和各自 SHA-256 由标签工作流生成。
- Docker 镜像在标签 CI 中构建并验证导出运行时，不上传镜像仓库。
- [标签构建 #35358991909](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35358991909) 的 Windows、Linux、Docker 与发布任务全部成功；Release 为非草稿预发布，稳定 Latest 仍为 `v0.4.2`。
- 发布详情与最终校验见 [v0.5.0rc2 Release Notes](RELEASE-NOTES-v0.5.0rc2.md) 和 [发布测试报告](TEST-REPORT-v0.5.0rc2.md)。

## 已完成的用户路径

1. 在产物检查器点击「查看版本差异」。
2. 查看版本历史卡片，识别当前版本、父版本及恢复来源。
3. 选择两个版本，查看源码差异、增删行数、内容大小与摘要。
4. 给选中版本命名，例如「客户确认稿」；空名称可清除标记。
5. 选择历史版本，点击「恢复为新版本」。当前稿保留为历史，旧稿的 HTML、Brief、素材与样式配置成为新版本的基础。
6. 继续反馈修改，版本号递增。恢复不会自动写入 Project Memory，仍需用户明确采用。

反馈修改、重跑生成和恢复都形成新版本。仅重跑质量验证不创建内容版本。重跑生成先校验 HTML，再替换当前产物；校验失败保留原稿。

## 数据与兼容

- `revisions/revN.html`：HTML 快照，保留文件换行符。
- `revisions/revN.json`：生成状态快照、名称、父版本、恢复来源、操作类型与时间。
- `.foxstate.json` 与 `output.html`：当前可编辑状态及预览产物。
- 老项目不强制迁移。下一次反馈或重跑会先保存当前版本的生成状态。
- 早期只存 HTML、没有生成配置的历史版本仍可比较与命名，界面明确说明无法完整恢复。
- 单份 HTML 在线处理上限为 2MB；源码差异展示最多 50,000 字符。
- 单个本地服务进程内，反馈、重跑、恢复及版本命名使用共享锁。恢复必须带当前版本号，过期操作返回 `revision_conflict`。
- 文件替换采用临时文件与原子重命名；写入异常尝试恢复原状态。跨多个文件的突然断电恢复、多个进程同时编辑同一目录，仍需独立事务日志和跨进程锁，不在本次保证范围内。

## HTTP v1 增量

| 方法与路径 | 请求 / 返回 |
| --- | --- |
| `GET /api/projects/{name}/revisions` | 当前版本、历史名称、父版本、恢复来源与可恢复状态 |
| `GET /api/projects/{name}/diff?from=0&to=1` | 两版差异、摘要及 SHA-256；省略参数时比较当前与上一版 |
| `PATCH /api/projects/{name}/revision-label` | `{"revision":0,"label":"客户确认稿"}` |
| `POST /api/projects/{name}/restore-revision` | `{"revision":0,"expected_revision":1}`；返回新的项目元数据 |

错误保持统一的 `code / message / request_id` 结构。缺失版本为 404，非法参数为 400，过期版本或缺失配置为 409，越界路径为 403。

## 验收入口

- `tests/test_revision_history.py`：恢复后继续反馈、重跑版本化、失败保护、并发冲突、旧数据兼容、UTF-8 / CRLF 文件保真与越界路径。
- `tests/test_server_project_api.py`：HTTP 版本查询、名称保存、恢复、错误与冲突。
- `tests/test_rc2_revision_accessibility_performance.py`：真实 Chromium 操作、名称转义、Tab 循环、Escape 焦点恢复、390px 手机布局、100 节点 / 99 连线操作与保存。
- 设置 `HTMLNINEFOX_TEST_EVIDENCE_DIR` 可输出桌面、手机截图与性能 JSON。最终结果见 [RC2 测试报告](TEST-REPORT-RC2-20260918.md)。

## 下一阶段顺序

1. 发布前补跨进程写入与断电恢复验收；进行持续使用测试及 macOS / iOS Safari 验收。
2. 补充 100 节点真实拖动帧耗时、预览 iframe 的资源预算与自动性能基线。
3. 再推进常用素材检索和可解释推荐、高保真 PPTX 导出。
4. 按长期路线推进 Windows / macOS 桌面壳，iOS 先做审阅与反馈，小程序和 Android 后置。
