# Html九尾狐 v0.5.0 RC1 测试报告

> 测试日期：2026-09-14
> 测试版本：0.5.0rc1

## 结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 全量 Python / API / 存储 / 安全 / 导出 / Chromium 测试 | **179 / 179 passed** | [pytest 日志](test-evidence/v0.5.0rc1-pytest.txt) |
| 内联 JavaScript 语法 | passed | [语法日志](test-evidence/v0.5.0rc1-inline-js.txt) |
| 发布版本一致性 | passed | [版本日志](test-evidence/v0.5.0rc1-release-version.txt) |
| Project Memory 浏览器闭环 | passed | [项目记忆截图](../assets/screenshots/v0.5.0rc1/project-memory-dialog.png) |
| 产物复用解释 | passed | [检查器截图](../assets/screenshots/v0.5.0rc1/memory-reuse-inspector.png) |
| 智能端口 / 整卡连接 | passed | [连线截图](../assets/screenshots/v0.5.0rc1/canvas-smart-linking.png) |
| 双向框选与实时预览 | passed | [框选截图](../assets/screenshots/v0.5.0rc1/canvas-directional-selection.png) |

## Project Memory 专项覆盖

1. 手动保存、读取、长度限制和清空。
2. 采用项目后提取品牌、受众、语气、禁忌、预设、主色与字体。
3. 同一项目重复采用不重复计数。
4. 本次明确要求覆盖长期记忆。
5. 关闭记忆后生成行为保持原样。
6. Analyze、Generate 与项目状态返回可解释的 memory_applied。
7. 长期记忆不包含 API Key、附件正文或完整私人反馈原文。
8. 浏览器完成打开弹窗、保存、复用生成、采用产物和采用状态刷新。

## 画布交互专项覆盖

1. 端口 48px 捕获与 76px 释放滞回。
2. 拖到目标卡片即可自动选择输入端口。
3. 精确端口可立即切换并覆盖旧的粘滞目标。
4. 左→右完整包含、右→左触碰选择、Alt 减选。
5. 框选过程中实时显示命中数量和模式。
6. 缩放、平移、快速松开和自适应连线路径回归通过。

## 结论

v0.5.0 RC1 的 Project Memory MVP 可正常使用，并保持 Beta 2 Recipe Run、画布、模板、导出和项目管理能力回归通过。RC2 继续推进 100 节点性能、产物版本差异和无障碍门禁。
