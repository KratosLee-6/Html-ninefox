# DeepSeek Harness 插件截图与测试证据

日期：2026-09-18。插件：`dsh-htmlninefox@0.1.0-preview.1`。Harness：`@deepseek-ai/dsh@0.1.5-rc.2`。

## 截图来源

- `harness-plugin-enabled.png`：将最终 `.tgz` 安装到全新的官方 Web profile 后启动 DSH，在“设置 → 插件 → 插件列表”搜索 `htmlninefox`；界面显示它是启用中的全局插件。
- `generated-poster.png`：同轮测试使用九尾狐离线规则生成中文海报，执行“标题大一点”的 dry-run 和真实反馈后，以长图方式导出。对应 PDF 与 PNG 的兼容性报告均为 100 分。

截图未使用模型 API Key，也未包含用户数据。DSH 截图使用隔离目录 `.codex_tmp/harness-release-home`；生成项目使用 `.codex_tmp/harness-output`，二者均不进入提交。

## 实际验证结果

| 检查 | 结果 |
|---|---|
| Cordis skill 注册、读取、重载、卸载 | 通过 |
| `npm pack` 后在独立中文空格路径安装 | 通过 |
| 最终 Release tarball 的 `dsh plugin add` | 通过 |
| 官方 `web` 模板 profile 的 `--dump-config` | 出现 `dsh-htmlninefox` 配置层 |
| 离线海报生成 → dry-run → 反馈修改 | 通过，创建 `rev1` |
| PDF 导出 | 通过，168130 字节，兼容性 100 分 |
| 完整 PNG 导出 | 通过，1030088 字节，兼容性 100 分 |
| GitHub CI | 插件 2/2、Python 199 passed、Chromium 22/22 |

完整安装、边界与发布校验见 [DeepSeek Harness 接入记录](../../DEEPSEEK-HARNESS-INTEGRATION.md)。
