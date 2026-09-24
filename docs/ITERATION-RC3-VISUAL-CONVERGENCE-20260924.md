# RC3 视觉与交互收敛记录

日期：2026-09-24  
状态：已实现并完成本地发布级验证  
范围：Web 工作台、移动任务视图、经典表单模式、视觉规范、测试发现配置与真实截图

## 目标

本轮把已经具备真实生成、反馈、恢复与导出能力的工作台收敛为更接近正式产品的界面。重点不是增加一组独立特效，而是让信息层级、响应式、组件状态、动效、图标和品牌在同一套 Pixel Garden 系统中工作，并让 README 直接展示本轮真实产品状态。

## 设计方法与约束

已实际读取并使用 RealDesign `design-to-product` Skill，对 `AGENTS.md`、原生 HTML/CSS/JavaScript 技术栈、工作台、经典模式、现有 Logo、Pixel Garden Token、动效系统和历史截图进行检查。项目已有清晰品牌基础，本轮没有调用 `design-inspiration`，也没有继承其他项目或示例的颜色。

技术决策：

- 保持原生 HTML、CSS 与 JavaScript，不为视觉动效迁移 React。
- 不引入 Anime.js；现有 CSS transition、keyframes 与 Web Animations API 已能覆盖状态反馈。
- Icon 资源本地打包，不依赖线上图标服务。
- 真实 HTML 产物继续在白色 iframe 中预览，主题样式不污染交付内容。

## 设计诊断结论

实施前最主要的问题是：顶栏入口过密；窄屏只是压缩完整画布；部分控件仍使用 Unicode/Emoji；桌面与经典模式存在两套视觉；节点在不同缩放级别仍渲染完整内容；按钮尺寸和焦点反馈没有形成统一门禁。

优先级按真实产品路径确定：

1. 先收敛输入需求与推进工作区两个主动作。
2. 再把平板和手机改为可操作的抽屉与任务视图。
3. 然后统一 Icon、组件状态、语义缩放和经典模式。
4. 最后用真实生成、检查器和导出中心截图验证，而不是只展示静态空壳。

## 已实现

### 信息架构

- 顶栏只突出“输入需求”和“推进当前工作区”。
- 诊断、经典模式、安装、新建工作区进入“更多”菜单。
- AI 模型、项目记忆和主题在桌面保留可见，窄屏收入菜单。
- 平板与手机提供明确的素材库和检查器抽屉入口，并同步 `aria-expanded`。

### 响应式与移动任务视图

- `>1180px`：完整三栏工作台。
- `901–1180px`：素材栏常驻，检查器为抽屉。
- `621–900px`：素材库与检查器均为抽屉。
- `≤620px`：显示移动任务视图，以当前工作区、两个主动作和节点列表代替缩小到不可读的完整画布。
- 点击移动节点卡会选中节点并打开检查器，浏览器测试覆盖该链路。

### 画布语义缩放

- `camera.z < 0.78`：摘要层，只保留节点识别信息。
- `0.78 ≤ camera.z < 1`：紧凑层。
- `camera.z ≥ 1`：完整表单、iframe 与编辑内容。

这样缩放不再只是几何变化，信息密度会随视距切换。

### 组件、状态与 Icon

- 桌面常用按钮提升至 36px；移动关键动作保持 40–44px。
- 统一 `:focus-visible` 陶土橙外环。
- selected、busy、success、error 状态使用一致的边框、颜色和文字反馈。
- 顶栏、HUD、节点类型、工作区动作等主要图标改为本地 SVG 注入。
- 图标按钮保留中文 `aria-label`；推进按钮固定可访问名称，避免桌面与移动文本同时被朗读。

### 经典表单模式

经典模式从黑紫/青色旧方案迁回 Pixel Garden：

- 纸张底色 `#F4F0E7`
- 面板 `#FFFDF6`
- 钴蓝 `#173C8F`
- 薄荷绿 `#49B894`
- 陶土橙 `#E57A3F`

页面使用真实狐狸 Logo，主要操作不再使用 Emoji，并补齐键盘焦点状态。

### 测试发现配置

根目录直接执行 `python -m pytest` 时，pytest 曾误进入历史 Windows 发布包的受保护浏览器缓存目录并在收集阶段失败。`pyproject.toml` 现已把默认测试范围限定为 `tests/`，并排除 `release`、`.codex_tmp` 与 `.git`。修复后根目录标准命令可稳定执行全量测试。

## 真实截图

截图位于 `assets/screenshots/v0.5.0rc3-visual/`：

| 文件 | 状态 |
|---|---|
| `workbench-paper-1440.png` | Pixel Paper 桌面三栏工作台 |
| `workbench-night-1440.png` | Pixel Night 桌面主题 |
| `input-dialog-paper.png` | 输入需求、文件与图片入口 |
| `selected-node-inspector.png` | 节点选中与检查器状态 |
| `workbench-tablet-768.png` | 768px 平板布局 |
| `workbench-mobile-390.png` | 390px 移动任务视图 |
| `workbench-mobile-library.png` | 完整展开的移动素材抽屉 |
| `generated-output-inspector.png` | 离线真实生成后的产物检查器 |
| `export-center-ready.png` | 真实产物进入导出中心 |
| `classic-pixel-garden.png` | 统一品牌后的经典模式 |
| `command-palette-search.png` | 命令面板搜索、活动项和快捷键状态 |
| `project-memory-saved.png` | 项目记忆真实保存与成功反馈 |
| `export-analysis-error.png` | 导出分析的服务端错误、禁用与错误 Toast |
| `revision-restore-complete.png` | rev0 真实恢复为新 rev2，并保留来源与成功 Toast |

### 四项状态证据

- 命令面板通过 `Ctrl+K` 打开，搜索“生成”后验证活动命令、键盘焦点和快捷键提示。
- 项目记忆通过真实保存接口写入品牌、受众、语气、禁忌、模板、主色与长期说明；保存状态使用 `role="status"` 和 `aria-live="polite"`。
- 导出错误使用不存在的项目调用真实 `/api/exports/analyze`，验证错误面板、禁用导出按钮、错误 Toast 和可访问状态区域。
- 版本恢复使用真实 rev0/rev1 文件与恢复 API，把 rev0 恢复为新 rev2，验证输出文件、节点 revision、恢复来源和成功 Toast。

## 验证结果

### 静态语法门禁

- `python scripts/check_inline_js.py`：通过，`index.html` 2 个内联脚本块、`motion-lab.html` 1 个脚本块语法有效。
- `node --check htmlninefox/server/static/canvas-productivity.js`：通过。
- `node --check htmlninefox/server/static/canvas-engine.js`：通过。
- `node --check htmlninefox/server/static/workbench-features.js`：通过。
- `node --check htmlninefox/server/static/workbench-ui.js`：通过。

### 四项状态与相关能力专项回归

```text
python -m pytest tests/test_workbench_visual_convergence.py tests/test_rc3_visual_evidence_states.py tests/test_motion_system.py tests/test_interaction_system.py tests/test_project_memory_rc1.py tests/test_rc2_revision_accessibility_performance.py tests/test_exports.py -q --basetemp .codex_tmp/pytest-rc3-evidence-focused -p no:cacheprovider
20 passed in 53.71s
```

### 全量回归

```text
python -m pytest -q --basetemp .codex_tmp/pytest-full-rc3-evidence -p no:cacheprovider
201 passed, 1 skipped in 102.94s
```

浏览器门禁覆盖 1440px 顶栏、768px 抽屉、390px 移动任务视图、控件尺寸、本地 SVG、语义缩放、抽屉可访问状态、移动节点到检查器、经典模式品牌 Token 和焦点环；新增专项门禁通过真实 API 覆盖命令面板、项目记忆保存、导出分析失败和 rev0 → rev2 恢复。截图通过 `HTMLNINEFOX_RC3_EVIDENCE_DIR` 由 `tests/test_rc3_visual_evidence_states.py` 可重复生成。

## 已知限制

- 本轮没有创建新的应用 Release；可安装预发布版仍是 `v0.5.0rc2`。
- 尚未完成 Safari、WebView2 实机验收。
- 产品内核仍需继续提取 CLI / HTTP / DSH 共用生成用例，并完成 durable Project commit、跨进程锁与断电恢复。
- 浏览器端状态仍集中在较大的页面脚本中，后续按 Project、Generation、Revision、Export 生命周期拆分。

## 下一阶段

1. 用两个真实调用方验证并确定共享生成用例 Interface。
2. 把生成、反馈、恢复和导出从 HTTP handler 中提取为可复用应用层。
3. 统一 durable write 与 Project commit，补跨进程和崩溃恢复测试。
4. 按产品生命周期拆分浏览器 Module，同时保持本轮视觉和浏览器门禁。
5. 核心稳定后决定 `v0.5.0` 正式版范围，并为新 Release 重新生成安装包、截图和发布说明。
