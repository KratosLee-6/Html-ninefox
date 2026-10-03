# Release Notes · v0.6.1

> **状态：已发布 · 2026-10-03**（v0.6.0 之后的第一个补丁版本）。
> 附件清单、SHA-256 校验值与下载链接以 [v0.6.1 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.1) 页面为准——它们由 CI 在打 tag 后生成，本文不复制一份会立刻过期的副本。

v0.6.1 是一个**以缺陷修复与内容资产补齐为主**的补丁版本：修掉两个真实缺陷，把 21 个「已交付但此前没有任何视觉证据」的功能补拍成图，并把品牌宣传片从静态截图换成真实操作录屏。

前序版本 `v0.6.0` 的用户可直接升级：Project schema、HTTP v1 与 Revision 历史完全兼容，数据目录不迁移、不覆盖旧项目。

## 修复

### 幻灯片编辑器：交错请求会写错节点（发布阻断级）

- **现象**：在工作台里先打开 A 的幻灯片对话框、在 GET 还在途时点开 B 的幻灯片，A 的响应后到，会用它自己的 `slides` 与 `revision` 覆盖 B 的编辑态；此时保存，`PUT /slides` 会把 A 的修订号写进 B 的节点。
- **根因**：`open()` 在 `await` 之后**无保护地**写 `draft.revision` / `draft.slides`，而 `open()` 开头又会整体重写 `draft`。既有的 `draft.busy` 只挡住重复点击保存，对交错请求无效。
- **修复**：给 `draft` 加请求序号（`request`），`open()` 在 `await` 前捕获当前值，`try` / `catch` / `close()` 三处出口一律 `if (request !== draft.request) return;`；`close()` 完整重写 draft 并自增序号，使关闭本身也能作废在途请求。结构与 `lifecycle-revisions.js` 的既有守卫同构。
- **门禁**：`tests/test_rc3e_lifecycle_modules.py::test_slides_open_discards_stale_response`——造两个真实 deck，在同一次 `page.evaluate` 内连发两次 `FoxSlides.open`，延迟先发的那次响应，断言标题与**全部可编辑文本**精确等于第二个 deck。
  - 断言写成**两侧序列化后同构比较**（页内 `|`、页间 `||`）是有原因的：两次 `run_expert` 可能落在同一秒而产生 `...-193022` 与 `...-193022-2`，用子串或只比首个文本节点都会恒真（生成器把 `Your Product · 发布会 2026` 写死在首位）。
  - **反向验证实测**：摘掉守卫 → 失败；恢复 → 6/6 通过。未经反向验证的门禁按无效处理。

### 提示词路径一致性：钉住而非修复

- `app.py::_prompt_and_inputs` 与 `application.py::_prepare_generation` 存在四处差异。逐条实测影响后，**只有「默认 prompt 串字面量在两处重复、当前值相同故结果一致」这一条构成真实风险**，其余三条为语义 no-op 或已有等价守卫。
- 因此本版**未改实现**，改为新增 `tests/test_prompt_path_consistency.py`（5 条）把两处路径钉住，使后续任何一侧改动若不同步即失败。未纳入断言的两点已在测试文件 docstring 写明理由。

## 新增

### 视觉证据补齐：23 → 23 张覆盖新增能力

- v0.6.0 的截图集有 13 张，另有 10 个**已交付但此前没有任何视觉证据**的功能。本轮按真实实现逐个实拍补齐：经典表单模式、命令面板、导出就绪态、生成取消、统一需求入口、移动端素材库、需求节点检查器、产物节点检查器、Project Memory、版本恢复。
- 采集受 `HTMLNINEFOX_V060_EVIDENCE_DIR` 控制，**未设置时只跑断言、一个字节都不写**，因此在 CI 上必跑且零副作用。
- **不沿用** `e2e_verify.py` / `canvas_e2e.py` 的 `assets/screenshots/v{__version__}/` 写死路径（运行即污染版本化发布资产）——那条路径只在显式发布时使用。

### 品牌宣传片：静态截图 → 真实操作录屏

- 50 秒中文版与 53 秒英文版**均为真实录屏**：由 `scripts/record_demo_film.py` 驱动 v0.6.1 的真实运行服务，光标真的移动、需求真的逐字打出、节点与连线真的逐个长出、导出中心真的被点开。字幕中的每个数字都是产品当场报出的（中文版置信度 67%、英文版 72%、需求分析 8ms、保存交付 40ms、兼容性 100、「未发现阻塞性兼容问题」）。
- 英文版是**独立录制而非翻译**：`--lang en` 用英文需求重新分析，故报出 72% 而非套用 67%。界面在两版中均为中文（工作台默认中文），分析返回的 chips 是产品自身输出，同样不改写。
- **唯一由 MiniMax-H3 生成的是开场约 3.5 秒抽象氛围**，提示词明确禁止任何文字。界面演示刻意不用文生视频模型：模型会把中文渲染成乱码、按钮位置随机、连线毫无逻辑，与「可正常演示」直接矛盾。
- 34 秒中英双语静帧版保留为无录屏渠道的备选；此前的 63 秒版与 44 秒静帧推拉版已删除。

## 验证

- 全量测试 **403 passed / 1 skipped**（v0.6.0 为 387，新增 16 条：C3 门禁 1 条 + C4 一致性 5 条 + 视觉证据 10 条）。
- 发布元数据一致性由 `scripts/check_release_version.py` 门禁：`pyproject.toml` / `htmlninefox/__init__.py` / `uv.lock` / 中英文 README 的版本与 tag 必须全部一致，不一致即构建失败。
- 打包流水线在 tag 上构建 Windows / Linux / macOS / Docker 四个 job，并在 Windows 上**真实启动**便携包（v0.6.0 起加入，见 `packaging/verify_portable.py`）。
