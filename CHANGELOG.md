# Changelog

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · Not affiliated with any company · MIT licensed.

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.6.3] — 2026-10-04 · 修复 v0.6.2 的发布阻断缺陷

> 补丁版本。产品行为、界面、项目 schema、HTTP 接口与 Revision 历史**均未改变**。
> 门禁：**414 passed / 1 skipped**；**变异测试 5/5 全部捕获**。
> 证据：[发布说明](docs/RELEASE-NOTES-v0.6.3.md)、[设计文档](docs/DESIGN-v0.6.2-ssrf-pinning.md)。

**Fixed**
- **v0.6.2 的出站抓取 100% 失败**（发布阻断）。三处缺陷：
  1. `conn.request(method, url, headers)` —— `http.client` 签名第三位是 `body`，
     headers 落进 `body` 位，`http.client` 把 dict 当 chunked body 迭代后抛
     `TypeError: can't concat str to bytes`。连接已建立、请求行已上线，然后客户端崩
  2. `do_open(http_class, req)` 缺 urllib 必传的 `context` 关键字，所有 HTTPS 请求建连前即崩
  3. `conn.host = host` 在 `connect()` 之前执行——`HTTPSConnection.connect()` 用
     `self.host` 同时决定**连接目标**与 SNI，等于把 socket 送回一次全新 DNS 解析，
     被钉住的地址被丢弃，**原 SSRF 缺陷在 TLS 上原样复现**
- HTTPS 改为**换 socket 工厂**（`_create_connection` 连已校验 IP）而非改 `conn.host`；
  顺序为「先钉 socket，再交主机名给 TLS」，两者反了都不成立
- 环境代理被显式移除（`ProxyHandler({})`）：设计吸收抓取**刻意不走环境代理**。
  连带修掉请求行退化为绝对形式、以及代理后唯一可达的站点抓不到
- `ips == []` 改为直接报错，不再静默退回未绑定路径——「没校验到任何东西」
  不等于「不需要钉」

**为什么 CI 没拦住**
> v0.6.2 发布时五个 job 全绿、39 个附件逐个下载重算 SHA-256 全部匹配、
> 元数据门禁通过，**而功能是坏的**。因为那 6 条门禁**全是拒绝型测试**，
> 没有一条让抓取成功返回过 body——「正确拒绝」与「彻底坏了」信号相同。
> 实证：把实现改回有漏洞的版本，6 条门禁**仍然全绿**。
>
> 这与 v0.6.0 的 Windows 便携包是同一形状。

**门禁 6 → 11**
- 新增**成功路径**（真起服务，断言 200 与正确 body）与 **TLS 端到端**（真证书 +
  真 socket，主机名解析不到服务，只有按钉住 IP 连才成功，而证书仍按主机名校验——
  一次请求同时证明 socket 半与 TLS 半）
- **变异测试**用五种方式破坏实现，**5/5 全部被捕获**。它翻出五条「门禁自己说谎」：
  只有拒绝型测试无成功路径、`pytest.skip` 自我放行、源码文本断言锁死有害代码、
  TLS 测试两分支结果等价、测试夹具自己补上了漏洞。**五条里有三条是我自己写的
  门禁在坏代码上报绿**——所以「11 条全过」不是提交依据，变异测试才是

**Removed**
- **一条被证伪的结构性门禁**：试图禁止关键功能路径只有拒绝型覆盖，
  以扫描源码文本实现，变异测试 **1/5**。已剔除并移出 `tests/`
  （留存为 `tests/test_gate_quality_gates.py.rejected`）。**一条无效门禁比没有门禁更糟**，
  它训练人忽略门禁；正确实现应当执行被检查的东西并断言结果，而不是 grep 源码

## [0.6.2] — 2026-10-04 · 安全补丁：SSRF 连接级 IP 绑定（P1-6）

> 纯安全补丁。产品行为、界面、项目 schema、HTTP 接口与 Revision 历史**均未改变**。
> 门禁：**409 passed / 1 skipped**（v0.6.1 为 403，新增 6 条真实 socket 门禁）。
> 证据：[发布说明](docs/RELEASE-NOTES-v0.6.2.md)、[设计文档](docs/DESIGN-v0.6.2-ssrf-pinning.md)。

**Fixed**
- **设计吸收出站抓取的 SSRF TOCTOU 窗口（P1-6）**：`validate_url` 早已解析并校验出合法 IP，但 `fetch_reference` **从未把它交给传输层**；`_default_transport` 交给 `urllib` 建连时，`urllib` 会**自己再解析一次 DNS**。两次解析之间，校验时解析到公网地址、建连时解析到 127.0.0.1，就会打开一条没人校验过的私网连接。原有的「响应后重新解析比对」是**事后检测**——响应会被丢弃，但字节已流过那条连接。
  - 修复：新增 `_PinnedHTTPHandler` / `_PinnedHTTPSHandler`，socket 连到已校验的地址，`Host` 头与 TLS 的 SNI、证书校验仍用真实主机名（虚拟主机与证书校验均不受影响）。重定向逐跳独立校验并绑定。响应后比对保留为第三层防御。
  - 新错误码 `intake_connect_failed`，失败不退化成 500。
  - **风险口径**：这是关闭 `v0.6.0` 已公开披露的残余风险，**不是新漏洞**。披露至今暴露面为 12 个内置设计源（地址由产品内置）；之所以提前关闭，是因为 v0.7「粘贴任意网址」会把暴露面放大到任意地址。
  - 模块 docstring 原先声称 rebinding「cannot swap in a private target」，**与实际行为不符**（它做到的是发现后丢弃），已改为如实描述。

**Added**
- **`tests/test_ssrf_connection_pinning.py`（6 条）**：全部走真实 socket。既有 SSRF 测试**全部注入假 transport**，没有一条验证真实连接连到了哪个 IP——这正是该缺陷活到今天的原因。
  - 门禁**第一版是假绿的**：resolver 固定返回公网时，`urllib` 连的是公网地址，压根够不到本机服务，什么都没证明。必须脚本化为「先公网、后 127.0.0.1」（攻击者的真实手法）才暴露窗口。改完后旧实现以 `intake_fetch_failed` 失败——**它真的去连了私网，只是没连上**。断言因此写成「必须因决策失败，不能因连接失败侥幸失败」。
  - 门禁自身第一版还有一处 `assert SECRET not in str(exc)`（bytes 比 str）抛 TypeError，**断言根本没执行**。
  - 三条为「接线门禁」，防「代码看起来修好了但没接到链路上」——与 C3 / C4 /「导出中心从来没有 PPTX 选项」同一形状。
- **`scripts/capture_core_shots.py` 版本推导**：原先把 tag、端口、输出目录写死，正是 v0.6.1 目录里混入 v0.6.0 截图的成因。现从包 `__version__` 推导，端口用环境变量覆盖。

**验证**
- 新门禁 6/6 通过；**反向验证**：摘掉绑定 → 红（提示「连接被尝试了，不是被阻止」），恢复 → 绿。
- 既有 62 条 intake 测试**全过且零放宽**。
- 实现中撞到三处 API 契约陷阱，已记入设计文档：`urllib` 的 `do_open(http_class, req)` 签名、`Request` 无 `.port`、HTTPS 不能与 HTTP 共用 helper（`HTTPSConnection` 用 `self.host` 做 SNI 与证书校验，绑定后必须把主机名改回，否则每个虚拟主机站点都会证书不匹配）。

## [0.6.1] — 2026-10-03 · 竞态修复 + 视觉证据补齐 + 真实操作录屏

> 补丁版本：项目 schema、HTTP 接口与 Revision 历史均不变，v0.6.0 用户可直接升级，数据目录不迁移、不覆盖。
> 门禁：**403 passed / 1 skipped**（v0.6.0 为 387，本轮新增 16 条）；发布元数据一致性通过。
> 证据：[发布说明](docs/RELEASE-NOTES-v0.6.1.md)。

**Fixed**
- **幻灯片编辑器交错请求会写错节点（发布阻断级）**：`open()` 在 `await` 之后无保护地写 `draft.revision` / `draft.slides`，而开头又整体重写 `draft`。开 A → GET 在途 → 开 B，A 返回后会用 A 的内容覆盖 B，随后保存把 revision 写进错误节点。既有的 `draft.busy` 只挡重复点击保存，对交错无效。现以请求序号守卫 `try` / `catch` / `close()` 全部出口，`close()` 自身也作废在途请求（`lifecycle-slides.js`）。门禁 `test_slides_open_discards_stale_response` 经**反向验证**：摘掉守卫即失败。

**Changed**
- **提示词路径一致性由「不管」改为「钉住」**：`app.py::_prompt_and_inputs` 与 `application.py::_prepare_generation` 的四处差异逐条实测后，只有默认 prompt 串字面量重复构成真实风险，其余为语义 no-op 或已有等价守卫。因此**未改实现**，新增 `tests/test_prompt_path_consistency.py`（5 条）把两条路径锁住。

**Added**
- **视觉证据补齐**：10 个已交付但此前无任何视觉证据的功能补拍为图，截图集 13 → 23 张。采集受 `HTMLNINEFOX_V060_EVIDENCE_DIR` 控制，未设置时零副作用。
- **`scripts/capture_core_shots.py`**：补上一直缺采集脚本的 5 张工作台主视图，**逐张断言顶栏徽标等于目标 tag**。这 5 张在 v0.6.1 最初是直接从 v0.6.0 复用的，验收时发现徽标写着 v0.6.0——那是对附件内容的假声明，已全部重拍。
- **品牌片改为真实操作录屏**：50 秒中文版 + 53 秒英文版（`--lang en` 独立录制，英文需求真实重分析故报 72% 而非套用 67%），由 `scripts/record_demo_film.py` 驱动真实服务录下。34 秒中英双语静帧版保留为无录屏渠道备选。
- **Release 附件纳入品牌片**：`.github/workflows/build-release-packages.yml` 的 `publish-release` 显式列举 4 支成片，避免中间版本被 glob 误带入。

## [0.6.0] — 2026-10-01 · 设计吸收流水线 + 可编辑 PPTX

> 原定发布窗口 11-01 ～ 11-14，本次为窗口前的稳定化完成发布，**实际发布日 2026-10-01**。附件与 SHA-256 随发布回读。
> 门禁（2026-09-29 最终复验）：**387 passed / 1 skipped**（v0.5.0 基线 303，本轮新增 84 条）；JS 语法 13/13；DSH 插件 2/2；Chromium 22/22；WebKit 22/22；Windows / Linux / macOS / Docker 四个构建 job 全绿，且 Windows 便携包**真实启动**通过。
> 证据：[S17 门禁报告](docs/test-evidence/v0.6.0-s17-20260929/README.md)、[双审计](docs/AUDIT-v0.6.0-20260928.md)、[发布说明](docs/RELEASE-NOTES-v0.6.0.md)。

**设计吸收（三条通道 → 素材审核台 → 六资产层）**
- 安全抓取框架：仅 http/https、解析校验拒私网/环回/重绑定、重定向逐跳过门、事后 rebinding 比对、体积上限、每源限速（`5de8d42`）。
- 源清单：内置 12 个设计源（四类 kind × 三档许可），支持用户目录同 id 覆盖（`d65b42c`）。
- 候选提取与审核台：骨架/令牌/意图猜测 → pending 审核；CSP 沙箱预览、批量采纳/拒绝、来源筛选、许可徽章、色板与大纲（`b5a722e`/`59a0cd3`/`8d3f34a`）。
- 手动导入增强：多 URL 批量（≤10 条逐条容错）+ ZIP 导入（24 文件/24MB 防穿越）（`4e6cdb3`）。
- 六资产层贯通：组件库（素材面板拖入生成）+ 渐变装饰（`97c88b7`）、动效原创样式（预算钳制 + reduced-motion 守卫 → motion-lab，`488f2e6`）、风格预设（→ 工作台风格面板，`82268ff`）、AI 分析通道（结构化 design brief + 标签，`9264a5c`）、吸收指标面板（`5f82bcf`）。
- 许可三档强制：inspiration-only 采纳跳过代码导入（`066905f`）。

**可编辑 PPTX（双层架构：工作台内编辑 + 服务端文件桥）**
- PPTX 文件桥：deck 产物 → python-pptx 受控映射 → 标准 .pptx（每页标题/要点文本框、对比度背景、页码脚注；扁平化如实上报）；往返验证文本可编辑（`3a3a384`）。
- 导出中心接入 pptx 格式 + 报告含可编辑元素数与降级清单（`e0d8f6d`）。
- 工作台内编辑闭环：幻灯片文本编辑 API（`PUT /slides` 带 `expected_revision` 并发保护，`4e893ea`）+ 结构化幻灯片编辑对话框（产物检查器「编辑幻灯片」入口，按页列出可编辑文本节点，保存后刷新 revision 徽章 / 检查器 / 实时预览，`a5d7a93`）。这是 v0.6 内可编辑 PPTX 的交付形态。
- Univer 可视化画布编辑器**降级为 S13U-b2 单独跟踪**：调研确认开源包只覆盖 slides 模型与 UI，PPTX 导入导出位于 Pro 档（`@univerjs-pro/slides*`）且 slides 无 UMD preset，集成需自建 vendor 构建管线。原 §七-B 的「Univer 作为工作台内可视化编辑层」决策据此修订，文件交付路径不受影响。

**质量与审计**
- 门禁：吸收压测 100 候选（创建 0.28s / 列表 40ms）+ 路径穿越全拒（`8d920be`）；WebKit 通道（Safari 引擎 22/22）+ Chromium 双通道 22/22；topbar 定位器歧义修复（同提交）。
- 双审计：mattpocock 四维（7 P1 中 5 修、2 记录）+ Mimosa deep（SSRF 设计性缓解 + 残余披露，见 [AUDIT-v0.6.0](docs/AUDIT-v0.6.0-20260928.md)）。

**发布前设计收口（2026-09-29，实拍审计后补做）**
- **尺度 token 收敛**：工作台原本有 17 种字号、7 种字重（含 560/650/800 非标称）、140 余个硬编码间距值。现收敛为 7 档 `--fs-*`、4 档 `--fw-*`，间距 142 个值走 `--space-*` 尺度（`2px` 作为发丝线保留）。分两步落地：先改位移 ≤1px 的网格内值，再由视觉评审决定 10/6/14/18px 的 2px 位移并留 8 张前后对比图（`docs/evidence/spacing-20260929/`）。运行时去重后实际只剩 6 种字号。
- **设计体检门禁**（`tests/test_design_health_gates.py`，6 条）、**版式与信息层级门禁**（`tests/test_layout_hierarchy_gates.py`，8 条）、**动效行为门禁**（`tests/test_motion_behavior_gates.py`，6 条）、**生成质量门禁**（`tests/test_generation_quality_gates.py`，50 条，覆盖板块划分顺序 / 内容质量 / 最终效果 / 端到端产物自足）。
- **动作派发表门禁**（`tests/test_action_registry.py`，4 条）与**写回协议门禁**（`tests/test_artifact_revision_writeback.py`，2 条）。
- **撤回两条此前的审计结论**：「两套 token 命名空间冲突」实为不同作用域（`pixel-garden-tokens.css` 随产物发布、`workbench-system.css` 属工作台外壳），且各自的间距刻度本就该不同——真实问题是前者承诺「各产物 @import」却从未被任何生成器引用，已订正其文件头；「40 处硬编码 px」实为 60 处间距声明，且初版把圆点直径、投影偏移等非间距属性混了进来。详见 [AUDIT-DESIGN](docs/AUDIT-DESIGN-20260929.md)。

**品牌宣传片重制（v0.6.0 实拍）**
- 中英双版品牌片整体重制（原 30s / 12 镜）：原版界面镜头取自 `v0.5.0` 截图，且开场氛围底板由 MiniMax-H3 生成。v0.6.0 界面收敛（字号 / 字重 / 间距尺度 token、首屏画布缩放 0.33→0.80、审核台改指标条、夜蓝主题对比度提升）后，原片已与实际产品不符。
- 新片的**界面画面没有任何一帧是生成的**：全部取自 `assets/screenshots/v0.6.0/` 的真实运行截图；标题卡与尾卡为 Playwright 渲染的静态卡，品牌标志渲染自 `htmlninefox/server/static/logo-mark.svg` 官方源文件。**刻意不用文生视频模型重做界面镜头**——模型会生成乱码中文文字，比真实截图更差。
- **开场为 MiniMax-H3 生成的抽象氛围镜头**（`opener-h3-2k.mp4`，8s / 2K / 16:9）：暖纸底、方格格线、钴蓝与薄荷光，**不含任何文字或界面**，然后 0.40s 交叉淡入标题卡。片中使用其中 4.4s。
- **取景改为留边而非裁切**：截图为 16:10、成片为 16:9，原先的 `crop` 把顶栏裁掉了，而顶栏正是 `v0.6.0` 版本徽标所在。现改用 `scale=...:force_original_aspect_ratio=decrease` + `pad`（品牌暖纸色），每个界面镜头的顶栏与版本徽标全程可见——观众能自己确认看到的是哪个版本。
- 合成脚本入库为 `scripts/make_promo_film.py`（原为本地临时脚本），使「本片由 v0.6.0 实拍合成」这句声明可被复现验证。
- **片长与画面稳定性按反馈重做（2026-10-03）**：63s / 21 镜版本被评价为「会无限抖动、前面很拖沓、时间太长、没有声音，不是很舒服」，四项各自对应一处实现取舍：
  - **去掉「无限抖动」**：`kenburns()` 移除 `zoompan` 的全部缩放，只保留 `scale` + `pad`。Ken Burns 在 UI 截图上的实际观感就是持续抖动；界面镜头现一律静态，运动只留给 H3 开场。
  - **压缩前段 + 砍时长**：63s / 21 镜 → **34.00s / 10 镜**（+ 标题卡、尾卡）。删掉独立的标语卡（标题卡已含其文案），开场由 8.5s 收到 4.4s。
  - **加声音**：全片铺器乐床 `brand-bed.mp3`（无人声，音量 0.16，2s 淡入 / 2.2s 淡出，末端 `alimiter=0.92`）；H3 开场的原生环境音保留并在交叉淡入处淡出。实测 `mean_volume -28.7 dB` / `max_volume -10.0 dB`。
  - **`validate_script()` 规则放宽**：由「每个功能都必须有镜头」改为「每个镜头必须对应 `CATALOGUE` 真实功能 + 镜头数 ≥ 8 + 同一功能不重复出镜」。**原来的全覆盖规则正是长度的来源**——它强制片子覆盖全部 21 项。未入选的 11 项由 README 与 23 张截图集承担说明，脚本内 `NOT_IN_FILM` 逐条列原因。
  - 另修 `NOT_IN_FILM` 与分镜表互相矛盾：其中「命令面板」「反馈迭代与版本历史 / 恢复」两条仍写着「v0.5.0 才拍到」，但这两项 v0.6.0 已实拍且已入片。该表是说明性文档而非门禁（无代码读取），已在注释中写明每次改分镜都要回查。
- 成片 **34.000000s / 1920×1080 / 850 帧 / 25fps / AAC 立体声 48kHz**。
- **「静帧不是演示」：改为实时录屏（2026-10-03 第二次返工）**

  34s 静帧片被评价为「**还是只有静态**，全靠截图介绍，不是很有诚意和可靠性」。诊断：那支片每一帧确实来自真实状态，但**呈现方式是静态帧加 Ken Burns 推拉**——鼠标不动、字不一个个出现、节点不冒出来。观众分不出它和幻灯片的区别，等于没做演示。**真实来源不等于真实过程。**
  - 改用 Playwright `record_video_dir` **实时录制真实会话**（[`scripts/record_demo_film.py`](scripts/record_demo_film.py)）：每次点击前 `page.mouse.move()` 走两段式让光标移动可见，文字用 `page.keyboard.type(delay=85)` **逐字打出**，步骤间留足停顿供观众阅读。
  - 演示完整主线：输入需求 → 分析（真实返回置信度 67%）→ 采纳并生成（节点与连线**逐个长出**，底部实时计时 8ms → 40ms）→ 产物 `rev0` → 导出中心（兼容性 100、「未发现阻塞性兼容问题」）。
  - 成片 **50.000000s / 1250 帧 / 1920×1080 / AAC 立体声 48kHz**，`mean_volume -28.6 dB` / `max_volume -9.3 dB`。字幕里的每个数字都是产品当场报出的。
  - **H3 刻意只用于开场 3.5s 抽象氛围**，界面演示全部实录：文生视频模型会把中文渲染成乱码、按钮位置随机、连线毫无逻辑，与「可正常演示」直接矛盾。
  - 制作脚本入库为 `scripts/record_demo_film.py` + `scripts/finish_demo_film.py`，使「本片是真实操作录屏」这句声明可被复现验证。
  - **英文版是独立录制，不是翻译**（`--lang en`）：英文需求真实输入并被真实分析，因此它报出的是 **72%** 置信度（中文版 67%），录屏 50.36s、成片 **53.000000s / 1325 帧**。两个会话之间不共用任何数字。界面在两版里都保持中文——工作台默认中文，这是产品事实；分析返回的 chips（落地页 / 首页 Hero）是产品自己的输出，也不改写。
  - 期间修掉四处实现缺陷：裁剪方向算反导致 `49.84s != 50.00s`；`-shortest` 因音轨略短**静默截掉最后几帧**（改 `apad` + `atrim=end`）；滤镜图标签数错（8 条字幕产出 `v7` 却引用 `v8`）；字幕中文三次渲染失败（`drawtext` 内联被控制台代码页转成乱码、`textfile` 指向 CJK 路径使整条 filtergraph 无法解析、该 ffmpeg 无 `charset` 选项），最终用 Pillow 渲染 PNG 再 overlay。
  - 整秒门禁的取整只尝试 `round()`（恒向上），曾误判英文版「无法凑整秒」；改为**上下取整都试、取可行者**（53s 只需 49.56s 录屏，而实录有 50.36s）。
- **同时弃用 44s 静帧推拉片**（`htmlninefox-brand-film-44s-16x9.mp4`）：它既非截图集也非演示，留着会与定稿混淆，已删除。34s 静帧片保留为无录屏环境下的备选。
- 片长由 `SCRIPT` 表推导（`film_seconds()`）而非写死，**且必须是整秒**。为此踩了三次：写死过一次（文件名标成 `60s` 而实际 40 秒）；改成推导后又出现 54.5s 而 `round()` 得到 54（文件名比成片短半秒）；加上开场后按 0.5s 浮点计算得 63.02s。现已把开场尾帧与交叉淡入**都按帧计数**——25fps 下 0.5s 是 12.5 帧，浮点必然漂：213 + 1375 − 13 = 1575 帧 = 恰好 63.00s，脚本在非整秒时直接报错退出。

### Added

- The v0.6 design-intake foundation: a source registry (`data/sources/*.yaml` with user overrides), a safe reference fetcher (http/https only, resolved-host validation rejecting loopback/private/reserved addresses, hop-by-hop redirect validation, post-fetch DNS-rebinding check, size caps, per-source rate limiting), an evidence store under `.library/intake/`, and three built-in gallery/motion sources with license classes.
- The PPTX file bridge (V0.6-S13): deck artifacts export to editable PowerPoint files via python-pptx — per-slide title/body text frames, solid backgrounds with contrast-aware text colors, page footers, and a report of flattened visuals; `pptx` optional extra added.
- Kind-specific intake extractors: motion sources capture transitions, animation shorthands and keyframe names; component sources capture section-level candidates with bounded snippets; typography sources capture size and line-height scales — each candidate records its source kind.
- Intake candidate extraction and a review store: fetched pages become pending candidates with title, intent guess, color/font tokens, and a section-level skeleton; `CandidateStore` persists them under `.library/intake/candidates/` with pending/approved/rejected status.
- A macOS (Apple Silicon) portable package: PyInstaller `.app` bundle with an icns icon, `ditto` zip, SHA-256, and a dedicated `macos` job in the release workflow; the desktop channel reports `macos-portable` and capabilities advertise macOS as `beta`.
- v0.6 new-feature visual evidence (V0.6-S20): `assets/screenshots/v0.6.0/` ships 7 real captures — the review workbench (pending list with all three license tiers, CSP sandbox preview, approved state with style-preset/component/motion actions), the motion lab intake card, the in-workbench slide editor, the export center PPTX run, and the `export-report.json` body. Regenerate with `HTMLNINEFOX_V060_EVIDENCE_DIR=assets/screenshots/v0.6.0 pytest tests/test_v060_visual_evidence_states.py`; without that variable the file runs as a pure assertion gate and writes nothing.
- A measured design health gate (`tests/test_design_health_gates.py`, 6 checks) that locks the interface defects found by the 2026-09-29 design review: the batch-fetch wiring, node-head badge layout, narrow-viewport step labels, WCAG AA contrast in both themes, and theme-aware foreground on accent surfaces.
- A layout and information-hierarchy gate (`tests/test_layout_hierarchy_gates.py`, 8 checks) covering the canvas fit model, first-load zoom, canvas width usage, template-card height/line clamps, the intake metric strip, filter selected state, the batch-import reachability path, and modal backdrop blur.

### Fixed

- **Windows 便携包与安装器一启动就崩溃（发布阻断级）**：`htmlninefox/desktop.py` 用了 `sys.platform` 却从未 `import sys`，PyInstaller 冻结入口一进入就抛 `NameError`，`/api/health` 永不回报。这条路径只有冻结入口会走，源码测试套件从不加载它——而打包流水线此前**只构建产物、从不执行产物**，于是一个能通过全部测试、四个构建 job 全绿、却完全无法启动的发布物被生产了出来。已修 `import sys`，并补两道防线：门禁 `tests/test_frozen_entry_gates.py`（5 条：静态扫描冻结入口未绑定的名字、冻结路径可导入、入口可执行、发行形态标注），以及真实启动产物的验证脚本 `packaging/verify_portable.py`（Windows job 在上传附件前实跑 exe，校验 health 回报的版本与发行形态、首页体积、六项静态资源与干净退出）。本机实测 73.8 MB 便携包启动后 health 回报 `0.6.0 / windows-portable`、首页 161 KB、静态资源全通、进程干净退出。
- **产物验证只查「文件在不在」，不查「内容对不对」**：接上实跑之后仍然留着一个洞——六条静态路由只断言「响应且大于 200 字节」。一份**用旧源码打出来的**包可以把六条路由全伺服出来、报出正确的版本号与发行形态、体积全部达标，却让用户拿到收敛前的界面与本该修复的失效按钮；而这一版修的几乎全是「服务端齐备、界面不可达 / 内容陈旧」这类问题，只查体积恰好查不到。现在 `verify_portable.py` 额外断言**冻结包经 HTTP 伺服出来的字节**里带着本版本真正新增或修复过的标记：尺度 token（`--fs-` / `--fw-` / `--space-`）、夜蓝主题对比度修复的 `--on-accent`、导出中心的 PPTX 选项、动作派发表 `FoxActions`、批量抓取转发函数、幻灯片写回的 `expected_revision`、revision 写回的唯一拥有者 `advanceNodeRevision`。收敛前的源码不具备这些符号，因此陈旧产物会在这里被抓住。

  > **反向验证**：把包内 `workbench-system.css` 改成一份「体积正常（12 KB）、但抽掉了全部尺度 token」的收敛前版本后——`/api/health` 仍报 `0.6.0 / windows-portable`、六条静态路由全部响应、六项体积检查全部通过——**只有新的内容断言拦住了它**。这道门禁确实会红，不是形式检查。
- **`verify_portable.py` 在非 UTF-8 控制台上 UnicodeEncodeError**：Windows 默认代码页为 cp1252，打印中文/全角字符时抛 `UnicodeEncodeError`，使「验证产物」这道防线在本地根本跑不起来。已固定 stdout 编码。
- **首屏画布把内容缩到 0.33 倍，右侧空出 666px**：`canvasFitInsets()` 把左上角那块浮层「工作区导航卡」当成一条**通高左栏**来避让（`left: 导航卡右缘` = 290px），于是 916px 宽的画布只剩 446px 可用，缩放被压到 0.33，内容缩成一小团、右侧大片空置——用户第一眼看到的是「这软件怎么这么小」。现在按各浮层的真实几何分别计入上 / 下 / 右三边（导航卡计入 top、HUD 计入 right、小地图计入 bottom），不再预留通高左带；fit 留白由 90px 收到 36px，小地图由 196×130 收到 150×100。首屏缩放 **0.33 → 0.80**，画布内容利用率 39% → 42% 且居中。
- **侧栏模板卡因英文描述与标题并排 flex 而高度跳到 179px、标题断词换行**：`.pal-name` 是 flex 容器，模板名与英文描述是兄弟节点，描述一换行就把标题挤成断词换行并把卡片撑高。两者改为上下堆叠、各自夹 2 行，卡片高度稳定（实测 3 行 → 2 行），缩略图 104px → 86px，`REAL HTML` 徽标从缩略图左上（压住内容）移到左下。
- **审核台的吸收指标是一行调试字符串、四个筛选项无选中态**：指标改为指标条（数字为主、标签为辅，待审 / 已采纳 / 已拒绝带状态色条），并补回区块标题「吸收指标」；筛选按钮按当前状态切换主/次样式并带 `aria-pressed`。同时把弹窗背景模糊由 12px 降到 6px——此前工作台被糊成一片，失去「我在哪个界面」的上下文。
- **界面动作名没有编译期约束，漏一个就成死按钮（C6）**：`index.html` 此前用 44 个手写的 `function foo(){ return window.FoxBar.foo(); }` 转发函数，把 HTML 与模板字符串里的 `onclick="foo(...)"` 接到 lifecycle 模块，两侧没有任何约束——引用一个漏登记的名字只会在用户点击时抛 `ReferenceError`，而服务端、单元测试与 CI 全绿。S20 期间的 `intakeFetchBatch` 死按钮（「多 URL 批量」整条能力在界面上不可达）就是这个形状。转发函数收成唯一派发表 `window.FoxActions`，并新增门禁 `tests/test_action_registry.py`：任何被 HTML/JS 引用却没登记的动作名都会让 CI 失败。顺带把动作属性里的内联 `document.querySelector(...).click()` 换成具名的 `openZipPicker()`，并补上 `esc()` 漏转义的单引号——它会进入 `onclick="...('${esc(id)}')"` 这类 JS 字符串，当前 id 被服务端正则限死故不可利用，但会误导后来者。**有意未做**：把 112 处 `onclick` 整体迁到 `data-action` + 事件委托，因为 `data-*` 取值一律是字符串而节点 id 是数字，132 处迁移的回归风险高于其收益；派发表 + 静态门禁已堵死该缺陷类。
- **Artifact 前进到新 Revision 的写回协议复制 3 份、其中 2 份漏持久化，刷新后 revision 回退**：这条协议此前被复制在 `sendFeedback` / `slides.save` / `generation.rerun` 三处且互不一致。前两处改了内存里的 `node.data.revision`，却既没写 localStorage 也没提交服务端快照——而页面刷新时画布优先从 localStorage 的 `fox-canvas-v3` 恢复，于是**用户刷新后看到旧 rev 号，服务端 Artifact 却已是新 rev**。「编辑幻灯片」正是 v0.6.0 对外宣称的核心能力（成果 G4），这条路径会直接让承诺失真。协议现收进唯一拥有者 `window.FoxRevisions.advanceNodeRevision(nodeId, revision, options)`，由它决定是否破缓存预览、是否重绘检查器、是否持久化、是否刷新项目列表；三个调用点只留各自业务语义。门禁 `tests/test_artifact_revision_writeback.py` 锁住两件事：协议不得再出现第二份拼装，以及「改幻灯片 → 刷新 → revision 不得回退」。修的过程中确认两点并已记入审计文档：只调 `persistWorkspaceNow()` 不够（它只 PUT 服务端、不写 localStorage）；初版回归测试用 `add_init_script` 清 localStorage，会在 reload 时把被测对象擦掉导致恒过。
- **「批量抓取」按钮是死按钮，多 URL 批量能力在界面上不可达**：`index.html` 的批量导入区用 `onclick="intakeFetchBatch()"` 调用了一个**从未定义**的全局函数——`FoxIntake.fetchBatch` 明明存在于 `lifecycle-intake.js`，只是没接到全局名上。点击必然 `ReferenceError`，于是 S04「多 URL 批量（≤10 条逐条容错）」这条 v0.6.0 主线能力没有任何用户可达路径，而服务端与其测试全绿。已补转发函数。
- **`test_rapid_double_advance` 在 CI 上反复超时（长期唯一的主导抖动源）**：该用例原本用两次 `page.evaluate` 往返来模拟「快速二次推进」，再等待 `#tl-status` 出现守卫提示。问题在于 `#tl-status` 有两个写入者——`flash()` 与任务轮询器（`lifecycle-generation.js` 每次轮询都覆盖它），两次往返之间隔着一次网络往返，轮询完全可能先把提示盖掉，断言就永远等不到；本地因为机器快、窗口小而复现不出来（本地约 1/8 概率，CI 上 5 次失败里 3 次命中）。现在两次推进在**同一个 `page.evaluate` 里同步发出**：`advance()` 在第一个 `await` 之前就同步写入 `activeJobs`，所以第二次必然命中守卫，且此刻首次轮询尚未开始、提示不会被覆盖。断言同时从「等一条瞬态文本」升级为核对**真正的不变量**——被拒绝的那次不提交第二个 `POST /api/jobs`。本地压力 15/15 稳定通过。
- **夜蓝主题的主按钮对比度仅 2.44:1**：`.btn-primary` 等五处把 `color:#fff` 写死，而夜蓝主题的 `--accent` 是亮蓝 `#76A5FF`，白字压在上面几乎读不出来——受影响的是「推进当前工作区」这个全站最重的 CTA。新增 `--on-accent` 语义令牌（纸白 `#FFFFFF` / 夜蓝 `#0C1B2E`），五处统一改用它，保留品牌配色不变。
- **弱化文字对比度不达 WCAG AA**：版本号、栏目标题、模板英文描述、数量角标、状态字形共用一个 `--text-tertiary`，纸白主题下只有 3.17–3.51:1，而它们又只有 9–11px（小字本就要求 4.5:1）。夜蓝主题另有 9.5px 描述文字停在 3.98:1。两套主题的该值分别调整为 `#59676D` 与 `#A0B6BE`，在各自全部底色上均达 AA。
- **画布节点头部把类型徽标压成竖排单字**：`.node-head` 是 `flex-wrap:nowrap` 且标题没有收缩下限，中文模板名几乎必然触发——徽标被压到 12×21，两个汉字上下堆叠。现在标题先 `text-overflow:ellipsis` 截断，徽标 `flex:0 0 auto` 保持完整。
- **窄屏进度条只剩无含义的圆点**：`@media (max-width:760px)` 把五个步骤名全部 `display:none`，390px 下整条进度只剩三个 √ 和连接线，占着约 50px 却传达不了任何信息。改为只隐藏已完成/未开始的步骤名，**当前**与**失败**步骤的文字始终可见。
- **工作区与通知的关闭控件过小**：`.ws-head button` 固定 `height:22px`、`.fox-toast-close` 22×22，均低于项目自己声明的 `--control-touch:44px`。工作区按钮提到 28px，通知关闭提到 28px，并在 `pointer:coarse`（触屏）下分别提升到 44px / 36px。
- **导出中心没有 PPTX 选项，可编辑 PPTX 链路用户不可达（V0.6-S20 门禁发现）**：服务端 `SUPPORTED_FORMATS` 与 `lifecycle-exports.js` 的 pptx 分支（`syncOptions` 收起纸张/倍率字段）早已就绪，但 `static/index.html` 的 `#export-format` 只登记了 `pdf` / `png`。也就是说 S14 的验收条件「UI 选择 pptx → 任务完成 → 报告列出可编辑元素数与降级数」从未真正成立——成果 G4 在界面上无法触达，缺陷却完全不可见，因为没有任何测试点击过那个下拉框。`#export-format` 现登记 `PPTX 演示（可编辑 · deck 产物）`，`renderAnalysis` 依据 manifest 的 `intent` 只对 deck 产物放开（服务端对非 deck 本就返回 `export_format_unsupported`，不制造必然失败的选项）。门禁断言该选项真实存在且可选中，采集脚本不再注入临时 option。
- **所有 typography 候选在抽取阶段抛 `TypeError`，许可第三档「开放许可」整体不可达（V0.6-S20 门禁发现）**：`extract_candidate` 通过 `KIND_EXTRACTORS` 统一以 `(evidence, html_text, style_blob)` 三参派发，而 `extract_typography` 只声明了两个形参，签名与派发契约不一致。typography 是 `data/sources` 中**唯一**的 `open` 许可来源（fontshare / google-fonts），意味着审核台的许可三档治理里「开放许可」这一档在真实使用中永远无法产生候选，成果 G1/G2 的档位覆盖名存实亡。已把签名对齐到统一契约（附带说明该形参不参与计算），门禁改为无条件断言三档齐全。
- **PPTX 导出结果区渲染出一行 href=undefined 的失效下载按钮**：`lifecycle-exports.js` 无条件把 `result.report` 追加到 `result.files` 之后，但 pptx 路径的 `files` 里已经包含了 `export-report.json`，其顶层 `report` 只有 `name`/`bytes` 没有 `download_url`，于是同一份报告被渲染两次、其中一次链接失效。现在只在 `report.download_url` 存在时追加，PDF/PNG 路径行为不变。
- **Deck 生成在装有 jinja2 的环境下退化为落地页，导致整条可编辑 PPTX 链路失效（V0.6-S17 门禁发现）**：`generate_expert` 把 `deck` 别名到 `templates/landing.html`，因此凡安装了可选 `templates` extra 的环境，deck 请求都会渲染成 hero/features/pricing 落地页，产物里没有 `<section class="slide">`。结果是 PPTX 文件桥（`export_deck_pptx`）、幻灯片编辑 API（`PUT /slides`）与导出中心 pptx 全部失去输入——即 v0.6 成果 G4「可编辑 PPTX」在该环境下必然失败，且失败点在生成端、报错点在导出端，极难定位。deck 现在保持 intent 忠实：落到原生 `generators/deck.py`，产出真正的分页结构（实测 7 页 / 24 个可编辑元素），与联盟 manifest 声明的 `fallback: local:deck` 语义一致。已补回归测试锁定该不变量。

## [0.5.0] — 2026-09-25 · 🎉 First Stable Release of the 0.5 Line

> Stable release consolidating RC3-B2/C/D/E: shared application use cases,
> crash-recoverable Project commits with cross-process locking, and isolated
> browser lifecycle modules. Verified with 238 Python tests, 22/22 Chromium
> acceptance on both bundled Chromium and the real system Edge engine, and a
> real generation + PNG export smoke on the packaged Windows executable.

### Added

- Shared `StudioApplication.generate()` request/result seam for CLI, HTTP, asynchronous Jobs, and DeepSeek Harness parameter mapping.
- Stable `prompt_required` and `generation_failed` application errors, typed verification, Recipe Run, Memory, and composition values.
- A tracked v0.5.0 delivery map with RC3-C, durable Project commits, browser lifecycle Modules, and final release gates.
- Shared `FeedbackRequest / FeedbackResult`, `RestoreRequest / RevisionResult`, and `ExportRequest / ExportResult` application Interfaces.
- A `htmlninefox restore` CLI command with expected-Revision conflict protection.
- A `durable` module with the single atomic-write primitive (fsync, retry-on-Windows-replace) and a cross-process file lock (msvcrt/flock, bounded timeout).
- A prepare/commit/recover journal for Project commits: interrupted writes roll back deterministically on the next `load_state`, and phantom revisions never enter history.
- A stable `project_busy` 409 error when another process holds a Project lock.
- Crash-safe generation publication: `run_expert` stages in a dot-prefixed `.gen-` directory and publishes by rename.

### Changed

- CLI generation now reuses Project Memory and the same application orchestration as the workbench while preserving environment-variable AI discovery.
- HTTP generation handlers now translate transport data and serialize results; attachment-only Jobs validate through the shared application seam.
- DeepSeek Harness documents and tests Generation, Feedback, Restore, and Export mappings, including `--expected-revision`.
- CLI and HTTP Feedback, Restore, and Export now delegate business orchestration to `StudioApplication` while preserving HTTP v1 and Revision behavior.
- Every Project-rooted writer (ProjectStore JSON, Project Memory, AI settings, Recipe Run, generation artifacts, `.foxstate.json`) now goes through the shared fsync-backed atomic write.
- Project rename, duplicate, and delete now run under the source Project lock, turning cross-process collisions into stable `project_busy` responses.

- Four browser lifecycle modules (`FoxProjects`, `FoxGeneration`, `FoxRevisions`, `FoxExports`) extracted from the workbench monolith with private draft state, namespace APIs, and race guards; one in-flight generation per workspace with a cancel control, and an export busy guard with stale-result tokens.
- A `[hidden]` CSS fallback so `.btn` display rules can no longer un-hide hidden controls.

### Fixed

- `StudioApplication.restore()` now holds the per-project lock again; the RC3-C HTTP migration had bypassed `ProjectStore.restore_revision()`, letting concurrent restores of one project pass the revision-conflict check together on the threaded server. Regression-covered by a concurrent-restore test.

### Verified

- Full local suite: `238 passed, 1 skipped` (12 durability + 4 lifecycle tests); Chromium e2e `22/22`; DeepSeek Harness: `2/2`.

---

## [0.5.0-rc3] — 2026-09-24 · Pixel Garden Visual Convergence

### Added

- RC3 Pixel Garden visual convergence with a simplified primary-action header, local SVG icons, semantic node zoom, and responsive desktop, tablet, and mobile task layouts.
- Reproducible Playwright evidence for the command palette, saved Project Memory, controlled Export Center errors, and restore-as-new-version completion.
- Fourteen real RC3 screenshots covering themes, dialogs, inspectors, generated output, export readiness, responsive layouts, error feedback, and recovery lineage.

### Changed

- Unified the workbench and classic form mode around the existing Pixel Garden paper, cobalt, mint, and terracotta design tokens.
- Standardized desktop and mobile control sizes, focus-visible rings, selected, disabled, busy, success, and error states without adding React or Anime.js.
- Added live status semantics to Project Memory and Export Center feedback regions.
- Limited pytest discovery to the project test suite so root-level runs do not enter protected caches inside historical Windows release bundles.
- Updated the README, UI guide, and RC3 iteration record with current pages, state evidence, screenshots, validation results, and the next product-engineering milestones.

### Verified

- Inline JavaScript syntax and standalone workbench JavaScript checks pass.
- 20 focused Playwright and product tests pass across visual convergence, commands, memory, motion, interaction, revisions, and export states.
- The complete local suite passes with `201 passed, 1 skipped`.

---

## [0.5.0-rc2] — 2026-09-18 · Revision History and Native Motion

### Added

- Version labels, source diffs, parent and restore lineage, and restore-as-new-version for generated projects.
- Native motion preferences for system, reduced, and off modes, plus a local `/motion-lab` with six interaction samples.
- Browser acceptance gates for keyboard focus, 390px layouts, and a 100-node / 99-edge canvas workflow.
- A separately versioned DeepSeek Harness plugin preview for generation, feedback, and PDF / PNG export workflows.

### Changed

- Feedback, regeneration, and restore now preserve HTML and generation-state snapshots instead of overwriting history.
- Progress feedback uses stable stage updates, bounded visible notifications, cancellable animation cleanup, and an eight-target decoration budget.
- Release documentation now separates the `v0.5.0rc2` application prerelease from the DSH plugin preview and the stable `v0.4.2` application.

### Fixed

- Reject stale concurrent restores with a revision conflict and protect the current artifact when validation or atomic replacement fails.
- Preserve legacy HTML-only histories while clearly marking revisions that lack enough state for a full restore.
- Prevent stale dialog focus callbacks and generation animation cleanup from affecting a newer interaction.

### Verified

- Full Python, HTTP, storage, generation, export, accessibility, performance, and Chromium suites.
- Chromium end-to-end generation, revision, canvas, and export workflows.
- Wheel isolation smoke, tagged Windows and Linux package builds, checksum publication, and Docker runtime verification.

---

## [0.5.0-rc1] — 2026-09-14 · Project Memory

### Added

- v0.5 interaction system with typed Toast feedback, reversible button busy states, accessible dialog focus management, and a global command registry.
- Ctrl+K now searches both workbench actions and canvas nodes with keyboard navigation.
- Browser regression coverage for notifications, busy states, command execution, node search, Escape handling, and focus restoration.
- Recipe Run records Analyze, Compose, Generate, Verify, and Deliver stages with timing, model/generator, fallback usage, and summarized inputs and outputs.
- Per-project `recipe-run.json` evidence, HTML quality-gate reports, parent run links, and partial Generate/Verify reruns.
- Local Project Memory for brand, audience, tone, forbidden patterns, preferred templates, colors, fonts, and adopted design decisions.
- Explicit adoption signals, memory management APIs, an editable memory dialog, and reuse explanations in analysis, Recipe Run, and the artifact inspector.

### Changed

- Canvas dragging is now fluid rather than continuously rounded to a 16px grid, with `Alt` available to temporarily disable snapping.
- Alignment and connection targets now use acquisition/release hysteresis to prevent jitter and flickering near snap boundaries.
- Smart linking now accepts a 48px port radius, a 76px release radius, and whole-card drops, while exact ports outrank sticky card candidates.
- Marquee selection now previews hits live: left-to-right requires full containment, right-to-left selects intersections, and Alt subtracts from the selection.
- Connection curves adapt their control distance to horizontal and vertical separation for smoother short and long links.
- Port geometry is derived from rendered bounds and converted to world coordinates, keeping connections aligned through zoom and pan.
- Fit-to-content preserves workspace navigator space and uses a 30% minimum zoom so generated content remains readable.
- The active workspace timeline now switches from a generic checklist to the actual Recipe Run and stage durations after generation starts.
- Job state reads and atomic writes share one lock, preventing Windows polling races from leaving jobs stuck at `starting`.

### Fixed

- Process the final pointer position before drag or connection release, preventing fast interactions from ending one frame behind.
- Keep port hit areas from stealing pointer events from card content and keep connection stroke width stable while zooming.
- Prefer a newly reached exact input port over a previous whole-card sticky target, preventing links from landing on a nearby wrong node.

### Verified

- 179/179 Python tests pass, including Recipe Run, interaction, canvas, generation, storage, security, diagnostics, and export coverage.
- 22/22 Chromium product checks pass across generation, workspaces, templates, themes, and the Export Center.
- 17/17 focused canvas checks cover workspace and card dragging, snapping, port connections, Recipe Run details, partial verification reruns, HTML preview, generation, feedback iteration, fit, persistence, and JavaScript errors.

### Planned

- 100-node performance, accessibility gates, artifact diffs, and version trees.
- High-fidelity PPTX, then constrained editable PPTX and semantic DOCX.

---

## [0.4.2] — 2026-09-08 · Export Center

### Added

- Local-first PDF and PNG export from generated HTML projects.
- Preflight manifest with pagination detection, compatibility score, dynamic-content warnings, and runtime diagnostics.
- Page-range parsing, paginated Deck export, long-page PNG, image scaling, PDF paper selection, and landscape mode.
- Persistent export jobs, secure download URLs, and per-run `export-report.json` files.
- Export Center UI in output/history inspectors and the `htmlninefox export` CLI command.

### Packaging

- Playwright is now a runtime dependency while browsers remain locally selected.
- Windows packages collect the Playwright driver and reuse Edge or Chrome.
- Linux offline wheelhouses include Playwright, pyee, and cross-platform greenlet wheels.
- Docker images include Chromium for deterministic server-side export.

### Verified

- 159 Python, API, storage, security, export, and browser tests pass.
- 22/22 real Chromium generation, canvas interaction, and Export Center checks pass.
- Wheel and Windows portable builds complete real PNG export smoke tests.
- Linux offline archives contain x86_64/aarch64 Playwright plus CPython 3.10–3.13 platform wheels.

### Architecture

- Adopted a routed `Analyze → Route → Render → Verify → Deliver` export pipeline inspired by ppt-master's workflow and quality-gate approach.
- Kept visual-fidelity exports separate from future editable PPTX/DOCX mappings.

## [0.4.1] — 2026-09-05 · Release Integrity Repair

### Fixed

- Unified package, CLI, API, Docker, installation documentation, and download names on version 0.4.1.
- Added a release metadata guard that rejects mismatched Git tags before packaging.
- Linux installers now receive their version from pyproject.toml during the build instead of a hard-coded value.
- Corrected the README server description from FastAPI to the actual local Python HTTP service.
- Repaired v0.4.1 test-evidence links and added the missing canvas-productivity.js syntax check.

### Packaging

- Windows release uploads now include both the installer and portable ZIP with checksums.
- Linux release uploads now include .run, .tar.gz, wheel, and checksums.
- Tag builds now verify the Docker image in a dedicated CI job.

### Verified

- 153 Python, API, storage, security, generation, and browser tests pass.
- 20/20 Chromium generation and workbench acceptance checks pass.

### Design

- Added an Export Center architecture for PDF, images, high-fidelity PPTX, editable PPTX, and semantic DOCX.

---

## [0.4.0] — 2026-09-05 · Pixel Garden, Workbench and Private Template Compounding

### Added

- Pixel Garden visual identity, paper/night themes, branded logo, and five original NineFox style presets.
- Real LLM runtime settings for OpenAI-compatible, MiniMax, Anthropic, and local-compatible endpoints.
- Web workbench and Docker deployment path.
- Local-only private template packages imported from one HTML file or a complete resource folder.
- Safe asset copying, multi-page detection, page-role mapping, design-token extraction, and private-template deletion.
- Canvas undo/redo, marquee selection, grouped movement, node locking, minimap navigation, and Ctrl+K search.

### Changed

- Private template pages, colors, fonts, source metadata, and design tokens now influence generated deliverables.
- Imported HTML previews run under a restrictive CSP sandbox.
- Usage counts and intent-aware ranking prioritize previously successful private templates.

### Verified

- 153 tests pass, including private-template security, canvas productivity, API, generation, and browser coverage.

---

## [0.3.0] — 2026-09-03 · 🎉 Third Major Release · Skill Alliance 3 PPT Skills

> 🎉 **v0.3.0 = v0.3.0b2 + 3 飞书绝活大会 PPT 技能集成**

### ✨ Added — 3 PPT Skills (from 飞书绝活大会)

- **🖼 [baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck)** (by [宝玉 JimLiu](https://github.com/JimLiu))
  - AI 画图生成每页 PPT · 17 套风格 · 图片版 PPT
  - 模板：`htmlninefox/templates/baoyu-slide-deck.html`
- **📑 [frontend-slides](https://github.com/zarazhangrui/frontend-slides)** (by [张咋啦](https://github.com/zarazhangrui))
  - 3 版首页选 · 避开 AI 紫渐变 · 单 HTML 文件
  - 模板：`htmlninefox/templates/frontend-slides.html`
- **🎨 [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates)** (by [张咋啦](https://github.com/zarazhangrui))
  - 28 套稳定模板 · 字体配色不动
  - 模板：`htmlninefox/templates/beautiful-html-templates.html`

### 🔧 Changed — 5 类意图 generate_expert

- `generate_expert.py` 升级到 5 类意图：landing + ppt_image + ppt_html + html_template + infographic
- `rules.py` 加 ppt_image / ppt_html / html_template 关键词触发
- 优先级链：联盟 skill > 本地模板 > 占位
- `data/alliance/` 新增 3 个 manifest 种子（baoyu-slide-deck / frontend-slides / beautiful-html-templates）

### 🙏 Acknowledgments (v0.3 新增)

- 🎨 **[宝玉 (JimLiu)](https://github.com/JimLiu)** — baoyu-skills / baoyu-slide-deck
- 🎨 **[张咋啦 (zarazhangrui)](https://github.com/zarazhangrui)** — frontend-slides / beautiful-html-templates / beautiful-feishu-whiteboard
- (继承 v0.2 起：歸藏 / 花叔 / tt-a1i)

### 🧪 Tests

- ✅ 4/4 集成测试 · 146/146 pytest · 20/20 Chromium E2E
- ✅ P0 shell 注入已修 · 12/12 安全测试

### 📦 下载

- Windows 安装器：`HtmlNineFox-Setup-0.3.0.exe`
- Windows 便携：`HtmlNineFox-Windows-x64-0.3.0.zip`
- Linux：`HtmlNineFox-Linux-0.3.0.run` / `.tar.gz`
- Python wheel：`htmlninefox-0.3.0-py3-none-any.whl`

> v0.3.0 release 暂复用 v0.3.0b2 资产；下次 CI 重新构建 v0.3.0 品牌包。

---

## [0.3.0b2] — 2026-09-01 · Real Template Gallery & Guided AI Composition

### Added

- Six original, real-HTML showcase templates inspired by Guizang editorial and Swiss layout methods, with page-level preview and extraction.
- Guided creation entry for text, documents, and images: analyze, recommend a composition, accept it, or continue with custom canvas assembly.
- Local AI model settings for OpenAI-compatible endpoints with secret-safe API responses and a built-in connection test.
- Persistent composition metadata for selected gallery, pages, attachments, skills, and recommendation mode.

### Changed

- Layout, content, and style palettes now prioritize real rendered HTML rather than wireframe-only thumbnails.
- Canvas generation consumes selected page blocks, uploaded context, skills, colors, fonts, and templates.
- PWA cache and cross-platform package version advance to Beta 2.

### Verified

- 146 Python/API/storage/security/browser tests pass.
- 20/20 real Chromium generation and workbench acceptance checks pass.
- Windows portable health, six-item gallery, wheel contents, Linux installer structure, and SHA256 manifests were validated.
- Screenshots and raw test logs are committed under `assets/screenshots/v0.3.0b2/` and `docs/test-evidence/`.

---

## [0.3.0b1] — 2026-09-01 · Cross-platform Installable Beta 1

### Added

- Unified `htmlninefox app` launcher with health-based browser opening and automatic port fallback.
- Windows portable PyInstaller bundle, branded icon pipeline, SHA256 output, and Inno Setup installer definition.
- Linux user-level self-extracting `.run` installer and inspectable `.tar.gz` package.
- Dockerfile, Docker Compose, uv launchers, desktop entry, and local-network deployment guidance.
- Packaging automation for current Windows and Linux release artifacts.

### Changed

- Windows portable builds keep configuration, cache, projects, and output in a movable `user-data` directory.
- Runtime health responses expose the distribution channel; Windows and Linux clients are now marked beta.
- Installation documentation now separates portable, installed, container, PWA, and shared-server modes.

---

## [0.2.5] — 2026-09-01 · Pixel Garden Brand Workbench

### Added

- Final editable SVG brand system: app icon, standalone mark, and horizontal lockup combining a pixel fox with HTML angle brackets.
- Pixel Paper and Pixel Night UI themes with persisted theme preference and synchronized browser theme color.
- Complete visual identity and UI specifications in `docs/VI.md` and `docs/UI-GUIDE.md`.
- Archived v0.2.4 workbench snapshot for design comparison.

### Changed

- Replaced the black-purple AI aesthetic with warm paper, cobalt, mint, night-blue, compact radii, fine pixel accents, and restrained offset shadows.
- Updated canvas grid, panels, nodes, workspaces, status components, palette colors, focus states, and responsive brand lockup.
- New workspaces now start with `fox-pixel-garden` instead of the legacy Vercel dark preset.
- PWA manifest, service-worker cache, static routes, package version, screenshots, and tests now target v0.2.5.

---

## [0.2.4] — 2026-08-31 · Workspace Management & Visual Systems

### Added

- Persistent workspace navigator with one-click locate, active-workspace state, direct editing, and per-workspace material counts.
- Workspace names, six identification colors, legacy snapshot migration, and whole-workspace dragging that preserves child positions.
- Per-workspace creation progress replacing the unusable global infinite-canvas timeline.
- Five original visual systems: Pixel Garden, Duotone Studio, Editorial Ink, Swiss Signal, and Soft Silver.
- Three real brand/UI direction boards with Html × nine-tailed-fox logo concepts.
- Design-source and license audit for Huashu Design and Guizang PPT Skill.

### Changed

- The primary “推进生成” action now targets the active workspace instead of the last-created workspace.
- Generated output nodes retain their originating workspace identity.
- Workspace snapping aligns against other workspaces and no longer jumps toward its own child nodes.
- Template cards expose their visual-system origin and render structure-level differences instead of token-only recoloring.

### Verified

- 135 Python/API tests, 19 isolated Chromium acceptance checks, and 30 multi-intent rich-preview renders pass.

---

## [0.2.3] — 2026-08-31 · Smooth Canvas & Live Template Preview

### Added

- Real HTML thumbnails for all six layout types and six built-in visual presets.
- Large preview dialog and a dedicated `GET /api/template-preview` endpoint.
- Left/right input and output ports with expanded hit targets and candidate highlighting.
- Grid snapping, edge/center alignment guides, and workspace containment on drop.
- A dedicated `canvas-engine.js` geometry module shared by drag, snap, ports, and edges.

### Changed

- Pointer movement is batched through `requestAnimationFrame` and persistence happens after the interaction instead of on every move.
- Node positioning uses one world-coordinate model and `translate3d`, preventing zoom-related DOM/model drift.
- Edge endpoints are measured from real port positions instead of fixed node offsets.

### Verified

- 28 focused Python/API tests and 11 real Chromium canvas/preview checks pass.

---

## [0.2.2] — 2026-08-31 · Recoverable Workbench

### Added

- Project rename, duplicate, details, and recoverable soft delete.
- Canvas Schema v1 with atomic server snapshots and automatic backup recovery.
- Persistent asynchronous jobs with queued/running/succeeded/failed/cancelled states.
- Privacy-conscious one-click diagnostic zip.
- Unified HTTP error contract with stable codes and request IDs.

### Changed

- Web generation now submits a job and polls its state instead of blocking on one long request.
- Project and workspace filesystem behavior is concentrated in `ProjectStore`.

### Verified

- Full pytest suite, JavaScript parsing, wheel resource checks, and a real async generation flow.

---

## [0.2.1] — 2026-08-31 · Cross-platform Foundation

### Added

- Installable PWA shell, manifest, service worker, application icon, and install guidance.
- Responsive mobile drawers and Pointer Events canvas interactions.
- `GET /api/capabilities` for future desktop and mobile clients.
- Real Python package source and tests in the public repository.

### Fixed

- Windows GBK terminal crashes when Rich prints emoji.
- Broken `brief list` / `brief add` CLI calls.
- Jinja2 is optional again; the native generator remains the zero-dependency fallback.
- Default LiteLLM config and all PWA/template resources are included in package data.

### Verified

- 90 pytest tests pass in both the development tree and public repository.
- Fresh user-directory smoke test generates a valid HTML artifact.

---

## [0.2.0] — 2026-08-29  ·  🎉 First Public Release

> 🦊 **First release with all 5 agents real, all 3 sinks real, all tests passing, ready for GitHub.**
> Inspired by Feishu 飞书绝活大会 methodology (Brief + 审美模板 + 具体反馈 三件套).

### ✨ Added — 5 AI Agents (全部真实实现)

- **`brief_expert`** — Parses free-form Chinese / English prompts into `BriefStandard v0.1` JSON
  - 5 required fields: Goal / Context / Content / Style / Constraints
  - 10 optional extensions (interaction / i18n / a11y / performance / etc.)
  - Real LLM call via LiteLLM router → offline-rules fallback (zero-downtime)
- **`style_expert`** — Picks `StyleProfile` from 5 candidate styles
  - Candidates: **Linear** (0.92 winner for SaaS) / **Vercel** / **shadcn/ui** / **Stripe** / **Apple**
  - Real LLM scoring + visual feedback panel (live tracking)
  - Outputs: palette + typography + radius + shadows + components
- **`asset_expert`** — Routes asset requests through Skill Alliance
  - Intent recognition → skill manifest matching → invocation
  - Fallback chain: alliance skill → local presets → minimal placeholder
- **`generate_expert`** — Renders HTML via Jinja2 + Brief + Style
  - Local templates (5 included: landing / dashboard / PPT / resume / poster)
  - Jinja2 fallback path for offline operation
  - 9.5 KB output for typical landing page (real HTML, not placeholder)
- **`feedback_expert`** — User feedback → structured suggestion + token extraction
  - Confidence scoring (high → actionable, low → ask user for clarification)
  - **No retry on low-confidence** (Codex-designed anti-pattern: don't hammer the user)

### 📚 Added — 3 沉淀 Libraries (sinks)

- **`brief_lib.py`** (117 LOC) — Historical Briefs for retrieval
  - CRUD: list / get / add / delete / search
  - JSON schema validation against `brief-standard-v0.1.schema.json`
- **`template_lib.py`** (116 LOC) — Jinja2 templates + style metadata
  - Auto-extract design tokens from HTML (colors / fonts / radius)
  - Search by tag (`linear` / `vercel` / `dark` / `light` / etc.)
- **`feedback_lib.py`** (112 LOC) — Scored feedback for next-run improvement
  - Deep-merge `tokens_extracted` (newest wins on same key)
  - Append/list/get/get_tokens_extracted

### 🔌 Added — Skill Alliance Router

- **`alliance/router.py`** (280 LOC, secure by design)
  - **P0 shell injection FIXED** — `subprocess.run(argv, shell=False)` + `shlex.quote()` + entry-prefix whitelist
  - 3 published alliance manifests in `~/.htmlninefox/alliance/`:
    - `guizang-ppt.yaml` — PPT generation (归藏)
    - `huashu-design.yaml` — High-fidelity prototypes
    - `archify.yaml` — Architecture diagrams (sequence / workflow / dataflow / lifecycle)
  - 12/12 security tests pass (shell injection / path traversal / param injection / command substitution all blocked)

### 🛠️ Added — Expert CLI

- **`htmlninefox`** CLI (`python -m htmlninefox`)
  - `expert` — Run 5-agent pipeline → 6 artifacts
  - `brief list / add / get / delete / search` — Brief library CRUD
  - `template list / get / search-by-tag` — Template library
  - `feedback --project <id> --note "..."` — Append structured feedback
  - `--version` → `htmlninefox, version 0.2.0`
- **6 working artifacts per expert run**:
  - `brief.json` (BriefStandard v0.1)
  - `brief.md` (human-readable summary)
  - `style.md` (style profile + design tokens)
  - `assets.json` (asset manifest)
  - `output.html` (real HTML, ≥5 KB)
  - `meta.yaml` (timestamp / cost / skill_used)

### 📖 Added — Documentation (5 docs · 14 KB total)

- `README.md` (233 lines) — Project pitch + 4 ASCII diagrams + quick start
- `docs/DESIGN.md` (182 lines) — Feishu methodology + 5-agent design philosophy
- `docs/ARCHITECTURE.md` (153 lines) — 5-agent contracts + Skill Alliance flow
- `docs/EXAMPLES.md` (200 lines) — 5 real-world scenarios (SaaS / dashboard / PPT / resume / poster)
- `docs/ROADMAP.md` (172 lines) — v0.3 → v2.0 timeline

### 🧪 Tests (测试)

- ✅ **4/4 integration tests pass** — end-to-end Brief → 6 artifacts
- ✅ **12/12 security tests pass** — P0 shell injection blocked + 11 other vectors
- ✅ **CLI manual verified** — `python -m htmlninefox expert "做一个 SaaS 落地页"` runs end-to-end

### 📸 Assets (GitHub README screenshots)

- 6 PNG screenshots (1600×900 / 1440×900 / 1200×800 etc.)
- 1 interactive xterm.js CLI demo (HTML, 19.7 KB)
- 1 60s terminal recording (GIF, 920 KB)
- 3 static reference screenshots (JPG)

### 🎯 Inspired by (灵感来源)

- **飞书绝活大会 BV1bLMX6HE7b** (B 站 · 23.0 万播放 · 2026-08-03)
  - "有了 Skill，不代表一句话就能得到好作品。真正拉开差距的，是清晰的 Brief、可复用的审美模板，以及一轮轮具体反馈。"
- **shadcn/ui** — Open code + design system philosophy
- **Refero.design** — Design research for the AI era

---

## [0.1.0] — 2026-08-22  ·  Skeleton + Agent Definitions

> Skeleton release — agent classes defined but not yet wired.

### Added
- Project skeleton (Python package layout)
- 5 agent classes (placeholder implementations)
- BriefStandard v0.1 schema
- Alliance manifest format (draft)
- 3 placeholder templates (landing / dashboard / resume)

### Known Limitations
- Asset agent returns hardcoded URLs
- Feedback agent is a stub (always returns score=0.5)
- No integration or security tests yet

---

## [0.0.1] — 2026-08-15  ·  Research + Planning

> Pre-alpha. Feasibility study + brief methodology design.

### Added
- 飞书绝活方法论 (Feishu Juehuo Methodology) — Brief + 模板 + 反馈 三件套
- BriefStandard v0.5 (early draft)
- Comparison study: vs shadcn / Lovable / V0 / Figma-to-code
- 5-agent design (concept only)
- Alliance router concept

### Notes
- No code yet. Pure research.
- This is the foundation that 0.1.0 and 0.2.0 build on.

---

## 🗺️ Unreleased (Planned for 0.3.0 — Month 1)

- Real LLM API key integration (OpenAI / Anthropic / Gemini) — currently offline-rules only
- Install + integrate real alliance skills (`pip install guizang-ppt` etc.)
- Web UI workbench (browser-based, drag-and-drop)
- 3 additional styles (terminal / glassmorphism / bauhaus)
- Template marketplace (community contributions)
- GitHub Discussions for community

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full plan (v0.3 → v2.0).

---

[0.5.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0
[0.2.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.2.0
[0.1.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.1.0
[0.0.1]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.0.1
