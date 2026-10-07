# Html九尾狐 v0.3.0 Beta 2 测试报告

> Test Report · 中文为默认说明，English summary follows.

- **测试日期**：2026-09-01
- **版本**：`0.3.0b2`
- **项目作者**：KratosLee · Html九尾狐项目组
- **本地验证提交基线**：`cf9412cb10d45fdf0f8e394c6ab607fa17dc8003`
- **结论**：Python 测试 **146/146** 通过；Chromium 真实验收 **20/20** 通过；Windows 安装器、Windows 便携包、Linux 与 wheel 发布包均已生成 SHA256。

## 测试矩阵

| 范围 | 结果 | 覆盖内容 |
|---|---:|---|
| Python / API 测试 | 146 passed | CLI、规则、生成器、模板、Token、项目 CRUD、软删除、快照恢复、Job、诊断、安全、AI 设置、上传输入、工作台浏览器流程 |
| Chromium E2E | 20/20 passed | 五类真实生成、两轮反馈、五类截图、Deck 翻页、工作区拖动、重命名、颜色、多工作区、11 视觉系统、双主题、JS 错误检查 |
| Windows 冻结包 | passed | `/api/health` 返回 `0.3.0b2`，`distribution=windows-portable`，图库返回 6 项，工作台扩展脚本存在 |
| wheel 内容审计 | passed | 6 套图库 HTML、图库 manifest、AI 设置、输入模块与工作台脚本均包含 |
| Linux 包结构 | passed | `.run` 自解压标记、安装脚本、离线 wheels 与项目 wheel 均存在 |
| 署名审计 | passed | 当前源码、交付镜像及 Beta 2 包统一为 `KratosLee · Html九尾狐项目组` |

## Chromium 20 项验收

1. Landing 生成
2. Dashboard 生成
3. Deck 生成
4. Poster 生成
5. Architecture document 生成
6. 反馈迭代 rev1：颜色与字体 Token 变化
7. 反馈迭代 rev2：参考预设切换
8. Landing 截图
9. Dashboard 截图
10. Deck 截图
11. Poster 截图
12. Architecture document 截图
13. Deck 键盘翻页
14. 工作区列表与预置场景
15. 工作区整体拖动，子节点保持相对位置
16. 工作区重命名与独立颜色
17. 多工作区导航与独立进度
18. 11 套真实视觉系统
19. Pixel Paper / Pixel Night 双主题
20. 工作台无 JavaScript 页面错误

## 原始证据

- [pytest 原始日志](test-evidence/v0.3.0b2-pytest.txt)
- [Chromium E2E 原始日志](test-evidence/v0.3.0b2-chromium-e2e.txt)
- [运行环境](test-evidence/v0.3.0b2-environment.txt)
- [发布包 SHA256](test-evidence/v0.3.0b2-release-sha256.txt)
- [产品截图目录](../assets/screenshots/v0.3.0b2/)

## 复现命令

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m pytest tests -q -p no:cacheprovider
python e2e_verify.py
```

---

# English Summary

Verification completed on September 1, 2026 for `v0.3.0b2`.

- **146/146** Python, API, storage, security, and browser tests passed.
- **20/20** real Chromium acceptance checks passed.
- Windows installer and portable health, six-item gallery, workbench assets, wheel contents, and Linux installer structure were validated.
- Current source, delivery mirror, and Beta 2 packages use the personal attribution `KratosLee · Html九尾狐项目组`.
- Raw logs, environment information, screenshots, and release checksums are committed as reproducible evidence.