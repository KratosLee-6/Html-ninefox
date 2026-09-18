# DeepSeek Harness 接入调研与首版交付

日期：2026-09-18。插件版本：`dsh-htmlninefox@0.1.0-preview.1`。

## 决策

建议做轻量生态入口：让 Harness 用户在对话中发现九尾狐，完成 HTML 生成、反馈迭代和 PDF / PNG 导出。先收集安装成功率、首份产物完成率、反馈修改是否有效及导出失败原因，再决定是否投入结构化工具、聊天内预览或独立插件仓库。GitHub topic 可以帮助发现，但不能保证安装量或反馈量。

首版是原生 Cordis **技能工作流插件**：`apply(ctx)` 调用 `ctx.skills.register()`，由 Harness 现有技能工具加载指令，再使用宿主命令工具调用 Python CLI。它不是仅改名的 Codex 插件，也没有增加专用生成工具或 MCP server。九尾狐 Python 应用和导出浏览器独立安装；Harness 的模型凭据不会自动传入九尾狐。

## 官方规则与上传位置

依据官方仓库提交 `ddefc45fbc7f8e46dd73185e68295696d1297887` 查阅；实现另用已发布的 Harness `0.1.5-rc.2` 验证。官方 HEAD 当时已是 `0.1.6-alpha.2`，不能把源码 HEAD 和 npm latest 当成同一版本。

| 项目 | 已核实规则 | 九尾狐选择 |
| --- | --- | --- |
| 插件入口 | ESM JS / TS 模块导出 `apply`，用 `inject` 声明服务依赖 | 纯 JS，注入 `skills` |
| 可安装插件 | `package.json` 声明 `dsh.bundle.patch`，YAML patch 插入插件行 | 独立子目录，包名 `dsh-htmlninefox` |
| 发布代码 | 作者自己的 GitHub 仓库 | 当前 `Html-ninefox/integrations/deepseek-harness` |
| 可下载安装包 | 官方支持本地 tarball | `npm pack` → `.tgz`，可上传本仓库 GitHub Release 的附件区 |
| 包注册表 | npm 可选，非唯一渠道 | 尚未发布；发布前核验名称归属，使用 `preview` 标签 |
| GitHub 安装 | git 依赖必须是可解析的 npm 包；TS 构建需 prepare 与用户授权 | 本目录直接运行 JS；当前根仓库是 Python 项目，不能用裸 `github:owner/Html-ninefox` 安装 |
| 被发现 | 官方建议仓库 topic `dsh-plugin` | 添加该 topic，README 提供截图、安装与反馈入口 |
| 向官方贡献 | 官方目前不接受外部 PR | 不向官方仓库提交插件 PR；用户问题走自己的 Issues，Harness 本身问题可到官方 Discussions |

源码、Release 资产和 npm 包是三个独立的发布动作。当前完成源码与本地 tarball；未发布 npm 包、未建立独立插件仓库、未上传 Release 附件、未向官方发布推广帖。

## 创建步骤与目录

```text
integrations/deepseek-harness/
  package.json          # dsh.bundle 元数据、包版本和打包白名单
  cordis.patch.yml      # 插入 dsh-htmlninefox 行
  index.js              # 注册技能，使用模块路径定位资源
  workflow.md           # 生成 / 修改 / 导出指令和适用边界
  README.md             # 安装、分发、验证范围和反馈入口
  LICENSE
  package-lock.json     # 固定测试依赖
  test/plugin.test.js   # 真实 Cordis / Harness 注册表与打包安装测试
```

包无需构建，生产环境无 npm 运行依赖、无安装脚本。`npm ci --ignore-scripts && npm test` 验证后，`npm pack --ignore-scripts` 生成 `dsh-htmlninefox-0.1.0-preview.1.tgz`。完整安装命令在 [插件 README](../integrations/deepseek-harness/README.md)。

在新的 Web profile 安装（先安装好 `dsh`）：

```sh
dsh --profile fox-demo --from-default-profile web --dump-config
dsh plugin --profile fox-demo add ./integrations/deepseek-harness
dsh --profile fox-demo --dump-config
dsh --profile fox-demo
```

此命令假定 cwd 是九尾狐仓库根目录。已有同名 profile 时换新名称。单独执行 `plugin add` 初始化的是 base profile，不自动包含 Web 界面。

## 本轮验证

| 验证 | 结果 |
| --- | --- |
| 真实 Cordis 4.0.2 + dsh-skill 0.1.5-rc.2 技能发现 / 读取 / 重载 / 卸载 | 通过 |
| `npm pack` 后在独立中文空格路径安装，读取包内资源 | 通过；2 项 Node 集成测试均通过 |
| 真实 `dsh plugin --profile ... add` | 通过；profile bundle 列表包含插件 |
| 从 `web` 模板创建 profile 并 `--dump-config` | 通过；Web 与九尾狐配置均存在 |
| Harness Web 启动 | 成功监听本机测试端口；未携带 token 的 HTTP 请求被鉴权拒绝，符合预期；未完成登录后 UI / 模型会话验收 |
| CLI 离线中文海报 → dry-run → 修改 → PDF → 长 PNG | 通过；产物 `document.pdf` 168130 字节、`full-page.png` 1030088 字节；两项兼容性报告均为 100 分 |
| 用户指定两组 pytest | **14 passed，12.10 秒** |
| 内联 JS 与 canvas-productivity / canvas-engine / workbench-features 语法 | 通过 |

测试 profile 使用隔离的 `.codex_tmp/harness-home`；本次没有修改用户现有 Harness 配置。测试服务已停止。没有调用付费模型，因此尚未验证“真实模型主动选用技能”的完整会话，也不宣称跨版本兼容。

安装过程发现的环境问题：直接另装内置 Web bundle 会遇到其依赖的构建策略拦截；最终使用官方 `--from-default-profile web` 复用内置组合，已成功。机器全局旧版 Python 包缺少 `export`，从本项目源码执行完整链路成功；插件指令已增加版本和导出命令检查，并固定已通过 CI 的应用源码安装版本。

CI 已加入插件测试步骤，与现有 Python / Chromium 验收一起运行。本轮未修改项目已有、尚未提交的 `SKILL.md` → `skill/` 迁移。

### GitHub 交付核验

- 源码已推送 `main`：[6dea899](https://github.com/KratosLee-6/Html-ninefox/commit/6dea8996ec125aefc1c60a1b69ec7e28d50c0ac2)。
- [GitHub Actions #35350016631](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35350016631)：**success**。
- Linux / Node.js 22：插件 **2 项通过**；Python / 浏览器 **197 passed，61.80 秒**；Chromium 端到端 **22/22 通过**。
- 此段为 CI 通过后的文档追记；npm、Release 附件和 `dsh-plugin` 仓库 topic 尚未发布或修改。

## 反馈与下一步

1. 小范围试用：用户在自己的 Harness 配置下完成海报 / deck / dashboard 各一个，报告安装、生成、修改、导出的结果。
2. 发布 `.tgz` Release 附件：复用本项目仓库；插件使用独立版本，避免误认为九尾狐主程序新版本。
3. 验证实际需求后，增加结构化工具：生成、反馈、导出分别注册 `ctx.tools`，处理取消、并发、路径边界和清晰错误。
4. 用户需要频繁安装时，再考虑独立仓库或 npm；有预览需求后再接 Harness 客户端扩展。

反馈入口是 [九尾狐 Issues](https://github.com/KratosLee-6/Html-ninefox/issues)。推荐包含版本、系统、复现步骤、预期/实际结果与脱敏日志；不自动上传内容或收集遥测。

## 官方来源

- [README：开发者预览与社区发现](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/README.md)
- [Contributing：暂不接受外部 PR；使用 dsh-plugin topic](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/CONTRIBUTING.md)
- [第一个插件](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/index.zh.md)
- [打包与安装：bundle、profile、npm、GitHub、tarball](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/publish.zh.md)
- [技能服务及注册契约](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/subsystems/skills.zh.md)
- [工具开发教程](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/tool.zh.md)
