# v0.6.0 发布候选测试报告

- 日期：2026-09-29（S20 实拍与发布前设计收口后复验）
- 验证对象：v0.6.0 发布候选（版本号已在 `pyproject.toml` / `htmlninefox/__init__.py` / `uv.lock` 切换为 `0.6.0`）
- 起点提交：`e5f3664`（V0.6-S17 门禁与两处缺陷修复）→ 后续经 20 余次提交推进至发布前状态
- 环境：Windows · Python 3.11.15 · Node v24.15.0 · Playwright chromium + webkit
- 关联文档：[发布说明](RELEASE-NOTES-v0.6.0.md) · [双审计报告](AUDIT-v0.6.0-20260928.md) · [S17 门禁证据](test-evidence/v0.6.0-s17-20260929/README.md) · [v0.6.0 计划](PLAN-v0.6.0-STABLE-20260927.md) · [设计审计](AUDIT-DESIGN-20260929.md) · [架构审计](AUDIT-ARCHITECTURE-20260929.md)
- 结论：**全部可本地执行门禁通过（387 passed / 1 skipped，v0.5.0 基线 303，本轮新增 84 条）；发布阻断项 0。**
- ⚠️ **本报告不是"已发布"报告**：v0.6.0 尚未发布。S20 截图实拍**已完成**（`assets/screenshots/v0.6.0/` 共 13 张）；S21 打 tag / 构建附件 / Release **未执行**。

## 一、发布候选结论

| 门禁 | 命令 | 结果 |
|---|---|---|
| Python + 浏览器测试套件 | `python -m pytest tests -q -p no:cacheprovider` | ✅ **387 passed, 1 skipped**（约 254s） |
| JavaScript 语法 | `node --check` ×13 个 static JS + `python scripts/check_inline_js.py` | ✅ 13/13 通过；inline 块 index.html 2 块、motion-lab.html 1 块通过 |
| 打包产物实跑 | `python packaging/verify_portable.py` | ✅ Windows 便携包 73.8 MB 真实启动：health 回报 `0.6.0 / windows-portable`，首页 161 KB，六项静态资源全通，进程干净退出 |
| 四平台构建 | CI `build-release-packages.yml` | ✅ Windows / Linux / macOS / Docker 四个 job 全绿 |
| 发布元数据一致性 | `python scripts/check_release_version.py` | ✅ consistent |
| DeepSeek Harness 插件集成 | `npm ci && npm test`（`integrations/deepseek-harness`） | ✅ **2/2**：registry 发现/加载/重载/卸载；发布 tarball 在无源码、无生产依赖下可用 |
| Chromium 验收 | `python e2e_verify.py` | ✅ **22/22** |
| WebKit / Safari 引擎验收（S18） | `HTMLNINEFOX_E2E_ENGINE=webkit python e2e_verify.py` | ✅ **22/22** |
| 100 节点 / 20 revisions / a11y | 包含在 pytest 套件内（`test_rc2_revision_dialog_accessibility_and_100_node_gate` 等） | ✅ 通过 |
| 吸收压测（S16，`8d920be`） | 100 候选含畸形 HTML | ✅ 创建 0.28s / 列表 40ms / 路径穿越全拒 |

Chromium 与 WebKit 两通道均 22/22，**无引擎差异清单需要列出**。

> 说明：发布元数据门禁在 S19 阶段执行时版本号仍为 `0.5.0`（判定为 consistent）；切换到 `0.6.0` 后已复验 `check_release_version.py` 与 `check_release_version.py --tag v0.6.0`，均返回 consistent。

## 二、复现命令

```bash
python -m pytest tests -q -p no:cacheprovider
node --check <13 个 static JS>
python scripts/check_inline_js.py
python scripts/check_release_version.py
(cd integrations/deepseek-harness && npm ci && npm test)
python e2e_verify.py
HTMLNINEFOX_E2E_ENGINE=webkit python e2e_verify.py
```

## 三、吸收流水线专项验证

### 3.1 压测与安全面覆盖

| 项目 | 结果 |
|---|---|
| 100 候选（含畸形 HTML）批量创建 | 0.28s |
| 候选列表读取 | 40ms |
| ZIP 导入路径穿越 | 全量拒绝（24 文件 / 24MB 上限） |
| 多 URL 批量导入 | ≤10 条、逐条容错（`4e6cdb3`） |
| 预览通道 | `sandbox=""` + `default-src 'none'` + nosniff 三重实现，含头等测试 |
| SSRF 防护 | 仅 http/https；解析校验拒私网/环回/保留地址；重定向逐跳过门；事后 rebinding 比对并丢弃；体积上限；每源限速 |
| 许可三档 | inspiration-only 采纳时跳过代码导入（返回 `gallery_skipped`），非仅展示，为强制行为（`066905f`） |

### 3.2 审计处置摘要

- **Mimosa deep 静态扫描**：2 个 high（SSRF，指向 intake 抓取的动态 URL）。处置为**设计性缓解 + 残余风险披露**：抓取侧已有四层防护（API 边界 `validate_url` → fetch 内再校验 → 逐跳重定向过门 → 事后 rebinding 比对 + 丢弃），扫描器无法建模自定义校验故仍标记。依赖告警 **0**（14 包）。另有 20 条针对既有测试 fixture 的 SSRF/凭据命中（127.0.0.1 集成测试与脱敏假 key）已逐条核实为误报。
- **真实残余风险 P1-6（已披露，非静默忽略）**：校验用 IP 与实际连接 IP 是两次独立解析，理论上存在绑定前的置换窗口。缓解现状与该限制已写入审计报告；**连接级 IP 绑定（自建 HTTPConnection 直连校验 IP）列为 v0.6.x 首项**。
- **mattpocock 四维复审**：P1 共 7 项，5 项已修复落地（`license_class` 强制、来源筛选 status 误用导致列表恒空、`candidate_id` 主机名归一 + 中文 ZIP 导入、颜色令牌归一为 `#RRGGBB` 堵死色板 CSS 注入外联、components/motion 导入端点补 UI 按钮、AI 分析 busy 态）。P1-6 为残余披露项；P1-7（intake 编排仍约 165 行留在 `_Handler`，应提为 `IntakeService`）记入 v0.6.x。P2 批次共 20 项已记录并排入 v0.6.x（其中五项在审计中顺手修复），其中 P2-10 / P2-12 / P2-13 为低风险易修项优先。

## 四、可编辑 PPTX 专项验证

| 验证点 | 结果 |
|---|---|
| deck → pptx 往返 | 通过；导出后文本可编辑 |
| deck 产物结构（修复缺陷 1 后） | 实测 **7 页 / 24 个可编辑元素** |
| 降级报告 | 导出报告含可编辑元素数与降级清单，扁平化如实上报 |
| 幻灯片编辑 API | `PUT /slides` 生效，`expected_revision` 并发冲突保护生效（`4e893ea`） |
| 工作台内编辑闭环 | 产物检查器「编辑幻灯片」→ 按页编辑可编辑文本节点 → 回写 → revision 徽章 / 检查器 / 实时预览刷新（`a5d7a93`） |
| 有 / 无 jinja2 双环境 | deck 渲染保持同一分页结构（回归测试锁定，见下节） |

## 五、本轮发现并修复的缺陷

### 缺陷 1（严重 · 发布阻断级）：deck 被别名到 landing 模板，整条可编辑 PPTX 链路失效

- **根因**：`htmlninefox/experts/generate_expert.py` 的 `_INTENT_TEMPLATE_ALIAS` 把 `deck` 映射到 `templates/landing.html`（注释写作"deck 用 landing 模板兜底（保留原行为）"）。Jinja2 模板路径一旦命中就会**先于**原生生成器返回，deck 请求被渲染成 hero/features/pricing 落地页，产物中没有任何 `<section class="slide">`。
- **影响**：PPTX 文件桥（`export_deck_pptx`）、幻灯片编辑 API（`PUT /slides`）、导出中心 pptx 格式全部失去输入——v0.6 成果 **G4「可编辑 PPTX」在装有 jinja2 的环境下必然失败**。失败点在生成端、报错点在导出端，定位极难。同时违反联盟 manifest `guizang-ppt` 声明的 `fallback: local:deck` 语义。
- **为何 CI 没发现**：CI 只装 `pip install -e ".[dev]"`，**不含 `templates` extra**，因此 CI 走原生 `generators/deck.py`，一切正常。属典型的"可选依赖改变主路径"缺陷。
- **复现证据**：在干净的 `a5d7a93` worktree 上运行 `python e2e_verify.py`，首行即 `[✗] 生成 landing`，随后 deck 翻页交互 30s 超时崩溃（等不到 `#cur` 页码 HUD）；同一命令在修复后 22/22 通过。
- **修复**：deck 恢复 intent 忠实，回落到原生渲染器产出真正的分页结构（实测 7 页 / 24 个可编辑元素），与 `fallback: local:deck` 一致。新增回归测试锁定不变量：`tests/test_pptx_export.py::test_deck_generation_stays_intent_faithful_with_or_without_jinja2`。

### 缺陷 2（轻）：e2e doctype 判断大小写敏感

- **现象**：`e2e_verify.py` 断言 `html.startswith("<!doctype html>")`，而原生生成器输出小写、templates 家族输出大写 `<!DOCTYPE html>`。HTML doctype 按规范大小写不敏感，结果是装 / 不装 jinja2 会走到不同渲染路径并产生相反的门禁结果。
- **修复**：断言改为大小写不敏感比较，与渲染路径解耦。

## 五之二、S20 与发布前收口新增的门禁

本轮在截图实拍与实测审计中拦下的问题，绝大多数形态一致：**服务端能力已实现齐备，界面却没有可达入口，也没有任何测试点击过它**。完整清单见[发布说明 · 修复](RELEASE-NOTES-v0.6.0.md#修复)，此处只列门禁构成：

| 门禁文件 | 条数 | 锁定的不变量 |
|---|---:|---|
| `tests/test_design_health_gates.py` | 6 | 对比度双主题、字重尺度、主题前景色、节点头部、窄屏步骤、批量抓取可达 |
| `tests/test_layout_hierarchy_gates.py` | 8 | 画布避让模型、首屏缩放、宽度利用率、卡片高度与夹行、指标层级、筛选选中态、背景模糊 |
| `tests/test_motion_behavior_gates.py` | 6 | 节奏预算、降级真的停播、取消无残留、页面隐藏中止、并发上限 |
| `tests/test_generation_quality_gates.py` | 50 | 板块划分顺序、内容质量、最终效果、端到端产物自足 |
| `tests/test_action_registry.py` | 4 | 动作名唯一登记、引用必可解析 |
| `tests/test_artifact_revision_writeback.py` | 2 | 协议唯一拥有者、改幻灯片后刷新 rev 不得回退 |
| `tests/test_frozen_entry_gates.py` | 5 | 冻结入口未绑定名字静态扫描、冻结路径可导入、入口可执行、发行形态标注 |
| **合计新增** | **84** | v0.5.0 基线 303 → **387** |

> 门禁纪律：每条新门禁都做过**反向验证**——去掉对应修复后测试必须变红，否则视为无效门禁并重写。这条纪律是必要的，因为本轮被拦下的多数缺陷在「全部测试绿 + CI 绿」的情况下依然存在于产品里。

## 六、遗留观察（不阻断发布）

1. `tests/test_integration.py::test_feedback_token_extraction` 在一次全量运行中失败，单独运行与后续全量运行均通过，疑似受全量时长 / 执行顺序影响的偶发项；目前无稳定复现路径。**在 v0.6.x 继续观察**，若再现则定位 `FeedbackLib` 深合并路径的时间相关行为。
2. `e2e_verify.py` 运行时会按 `__version__` 写入 `assets/screenshots/v<版本>/`；本轮执行曾覆盖 `v0.5.0` 下 3 张已跟踪的发布截图（已 `git checkout` 还原）。S20 起已改用 `HTMLNINEFOX_V060_EVIDENCE_DIR` 显式指定输出目录，不再污染版本化发布资产。

## 七、结论

- v0.6 的吸收流水线（S04–S12）与 PPTX 链路（S13 / S14 / S13U-a / S13U-b）**未让既有能力退化**，Chromium 与 WebKit 双通道均 22/22。
- 发布阻断项 **0**。本轮拦下的发布阻断级缺陷是 **Windows 便携包与安装器一启动就崩溃**（`desktop.py` 用 `sys.platform` 却从未 `import sys`），根因是打包流水线只构建产物、从不执行产物；现已修复，并新增冻结入口静态门禁与 `packaging/verify_portable.py` 真实启动验证。Windows 便携包（73.8 MB）已在本机实跑通过。
- 建议将"可选依赖不得改变主渲染路径"列入 Definition of Done。
- **本轮尚未完成、不可据本报告认为已发布的事项**：
  - **S21 发布动作**（tag `v0.6.0` → CI 构建 Windows / Linux / macOS / Docker 附件 → GitHub Release 挂附件与 SHA-256 回读 → 关闭 Issue #7）**未执行**。
  - 因此本报告不包含 v0.6.0 的附件清单、SHA-256 校验值或下载链接；目标发布日期仍为 **2026-11-08**（窗口 11-01 ～ 11-14，含 7 天稳定化窗口 M5：11-01 ～ 11-07），**尚未发布**。
  - **未实跑的产物**：本机为 Windows，Linux 与 macOS 包仅验证构建成功与 SHA-256；安装器（`Setup.exe`）同样只验证构建。CI 中亦无此步骤。
  - DOCX 语义导出（S15）已出列至 v0.6.x，不在本报告验证范围。
