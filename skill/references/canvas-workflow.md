# 🎨 无限画布创作全流程

> 出处：`htmlninefox/server/static/index.html`（画布主体）、`canvas-engine.js`、`canvas-productivity.js`、`recipe_run.py`、`server/app.py`
> 入口：`htmlninefox workbench` → <http://127.0.0.1:8620>

---

## 1. 画布是什么

一张**无限画布**（世界坐标 + `DOM transform` 只是渲染结果，不作为数据源）。
用户把创作素材当作**节点**摆上去，用**连线**表达「谁喂给谁」，
点工作区的 **▶ 推进** 就让整条链路跑一遍，最后落出一个**产物节点**。

```text
需求节点 ─┐
          ├─▶  ▶ 推进（拆解 → 组合 → 生成）  ─▶  产物节点  ─▶  导出中心
版式/内容/风格/文件/技能 ─┘
```

**为什么用画布而不是表单**：一条历史需求、一份参考文件、一个从别的模板抽出来的页面区块，
都能作为「配方」留下并复用，下一次只需要换掉其中一两个节点。

---

## 2. 节点类型（12 种）

`kindLabel()` 映射（`index.html:1133-1134`）：

| kind | 界面标签 | 作用 |
|---|---|---|
| `ws` | 工作区 | 容器；有名称、颜色、素材计数和 ▶ 推进按钮 |
| `requirement` | 需求 | 一句话需求，推进时**自动拆解**为「类型 + 风格 + 要点」 |
| `block` | 内容 | 单个页面区块（见下方 12 个区块） |
| `template` | 版式 | 真实 HTML 模板 / 页面配方 |
| `style` | 风格 | 视觉预设 |
| `color` | 色卡 | 主色覆盖（写入 `tokens.primary`） |
| `font` | 字体 | 字体族覆盖（`serif` / `sans` / `mono`） |
| `source` | 输入文件 | 上传的图片 / 文档（`mime`、`size`） |
| `file` | 文件 | 历史文件 / 附件引用 |
| `skill` | 技能 | 联盟 Skill 接管 |
| `output` | 产物 | 生成结果节点，挂预览、版本、导出、采用按钮 |
| `note` | brief | 笔记 / brief 卡片 |

**尺寸约定**（`addNode`，`index.html:1117-1118`）：
工作区 `880×540`；`output` / `file` 宽 `430`；其余节点宽 `226`。

### 2.1 十二个可用内容区块

`BLOCKS`（`index.html:791-796`）：

| ID | 名称 | ID | 名称 |
|---|---|---|---|
| `hero` | Hero 主视觉 | `table` | 数据表格 |
| `feats` | 特性网格 | `cover` | 章节封面 |
| `pricing` | 价格表 | `quote` | 大字口号 |
| `faq` | FAQ | `road` | 路线图 |
| `kpi` | KPI 指标 | `layers` | 架构分层 |
| `chart` | 柱状图 | `cta` | CTA 行动栏 |

---

## 3. 左侧素材库（五个 Tab）

`index.html:592-598`：

| Tab | `data-tab` | 拖进去变成 |
|---|---|---|
| **版式** | `layouts` | `template` 节点（真实 HTML iframe 缩略图） |
| **内容** | `blocks` | `block` 节点（可从完整模板中**单独抽取**页面） |
| **风格** | `styles` | `style` 节点（11 套预设，全部有真实预览） |
| **文件** | `files` | `file` 节点 |
| **技能** | `skills` | `skill` 节点（联盟 Skill） |

交互：**拖到工作区**，或**双击加入**。
顶部搜索框 `#search` 过滤素材（`placeholder="搜索…（拖到工作区，或双击加入）"`）。

### 3.1 导入私人模板

素材库上方两个按钮（`index.html:600-603`）：

```text
＋ 导入单 HTML      →  accept=".html,.htm"
▣ 导入文件夹        →  webkitdirectory multiple（含 CSS/JS/图片/字体）
```

导入后自动识别：多 HTML 页面 / `data-page` / `.page` / `.slide`，
并提取**页面角色、常见颜色、字体**。
私人模板仅保存在**当前输出目录的 `.library/gallery/`**，不会自动提交到 Git。
模板的**使用次数会成为下一次推荐信号**。

---

## 4. 推进流水线（核心）

`advanceWs()`（`index.html:1630+`）分三阶段。

### 阶段 1 · 需求拆解（Analyze）

```js
POST /api/analyze   { prompt, inputs }
```

前置校验：本工作区必须有 `requirement`（或 `note`）节点，
且 `text` 非空**或**至少带一个 `input_ids`；否则提示
`请先点顶部“输入需求”，填写文字或添加文件/图片`（`index.html:1639`）。

返回并展示（`index.html:1652`）：

```text
拆解 ✓ <内容类型> · 风格 <preset_id> · AI|规则 · 置信度 <confidence>
```

### 阶段 2 · 组合配方（Compose）

读取本工作区**用户实际摆放**的组合（`index.html:1655-1670`）：

| 节点 | 读取字段 | 送到后端的键 |
|---|---|---|
| `template` | `data.intent` / `data.template` / `data.preset` / `data.gallery_id` | `intent` / `template` / `gallery_id` |
| `style` | `data.preset` | `template` |
| `color` | `data.hex` | `primary` |
| `font` | `data.font` | `font` |
| `skill` | `data.title` | `skill` |
| `block`（可多个） | `data.blockId` / `data.text` | `blocks[]`（去重）+ 追加进 `prompt` |

**意图仲裁规则**：若版式节点的 `intent` 与拆解结果不一致，
且 `an.intent_confidence >= 0.55`，以**需求拆解结果**为准，
并提示 `需求指向<类型>，已按需求类型生成（所选页面配方继续生效）`。

`selection_mode` 判定：有 `gallery_id` 或存在区块节点 → `custom`，否则 `automatic`。

### 阶段 3 · 异步生成（Generate）

```js
POST /api/jobs   { prompt, inputs, intent, template, gallery_id,
                   blocks, skill, primary, font,
                   selection_mode, quiet_llm: false }
```

轮询 `job.progress` 实时更新按钮忙碌标签（`生成 <pct>%`）与节点进度环，
并把 `job.recipe_run` 写入工作区状态、刷新底部时间线。
完成后新增 `output` 节点，写入：

```text
preview_url / project / project_name / intent / preset_id
revision / feedback[] / gallery_id / blocks / selection_mode
recipe_run / verification / memory_applied
```

并自动连一条 `需求节点 → 产物节点` 的边。

---

## 5. Recipe Run（五阶段运行证据）

`recipe_run.py:16-20` 定义（阶段 ID、中文名、英文名、起止进度、是否支持局部重跑）：

| 阶段 | 中文 | 英文 | 进度区间 | 可局部重跑 |
|---|---|---|---|---|
| `analyze` | 需求分析 | Analyze | 8 – 22 | ❌ |
| `compose` | 组合配方 | Compose | 25 – 45 | ❌ |
| `generate` | 生成产物 | Generate | 48 – 72 | ✅ |
| `verify` | 质量验证 | Verify | 76 – 88 | ✅ |
| `deliver` | 保存交付 | Deliver | 92 – 98 | ❌ |

每个阶段记录：**状态、开始/结束时间、耗时、模型或生成器、是否兜底、脱敏后的输入输出摘要**。

- 状态实时通过异步任务返回，展示在当前工作区**底部状态条**与**产物检查器**。
- 项目目录写入 **`recipe-run.json`**，最近一次同时写进 `.foxstate.json`，重启后仍可查看。
- `Generate` / `Verify` 支持**局部重跑**：上游分析结果标记为**复用**、不重新消耗模型；
  重跑通过**父运行 ID**串联历史（为后续版本树 / 差异对比铺路）。

**Verify 的质量门禁**检查：文档声明、HTML/Body 结构、`viewport` meta、产物体积，
并给出**兼容性分数**。

---

## 6. 画布交互（v0.5 基线）

### 6.1 拖动与吸附

- 节点**自由拖动**，拖动过程中**不再**强制 16px 网格取整。
- 按住 **`Alt`** 临时停用吸附（包括连接目标吸附）。
- 对齐参考线使用 **7px 捕获 / 14px 释放**的磁吸滞回，避免临界位置反复跳动。
- 拖动热路径走 `requestAnimationFrame`；**持久化发生在交互结束后**。
- 指针松开前会处理**最后一帧坐标**，避免快速拖动结束时回跳。

### 6.2 端口与连线

- 端口坐标由**真实视觉边界**换算回世界坐标 → 缩放 / 平移 / CSS 位移后连线仍对准视觉中心。
- 连接目标 **48px 捕获 / 76px 释放**滞回。
- 可直接拖到**整张卡片**上；**精确端口始终优先于整卡候选**。
- SVG 连线使用**非缩放描边**，缩放画布后线宽保持一致。
- 贝塞尔曲线依据横纵距离**自适应弯曲**：短连线更紧凑，长连线更自然。
- 端口命中区域**主要向卡片外侧扩展**，不抢占正文区域的拖动。

### 6.3 框选

| 方向 | 规则 |
|---|---|
| 左 → 右 | 要求**完整包含**才命中 |
| 右 → 左 | **触碰即选**（intersection） |
| 按住 `Alt` | 从当前选择中**减选** |

实时显示模式与命中数量。

### 6.4 快捷键与其他

| 操作 | 效果 |
|---|---|
| `Ctrl` / `⌘` + 滚轮 | 缩放画布 |
| 拖空白区域 | 平移画布 |
| `Ctrl+K` | 命令面板：同时搜索**操作**与**节点**，上下方向键选择、`Enter` 执行、`Escape` 关闭 |
| `Shift` | 框选 |
| 撤销 / 重做 | 画布命令（也进 `Ctrl+K`） |
| 适配全部 | `fit-to-content`，为工作区导航器预留空间，**最低缩放 30%** |

其他能力：多选移动、**组合**、**锁定**、**小地图**、工作区整体拖动（内部节点保持相对位置）。

### 6.5 工作区

- 必须有**名称、颜色、素材计数和推进动作**。
- 可从工作区标题栏**或空白区域整体拖动**。
- **四种识别色**（`index.html:786-791`）：

| ID | 名称 | HEX |
|---|---|---|
| `garden` | 像素花园 | `#173C8F` |
| `mint` | 薄荷苗圃 | `#49B894` |
| `clay` | 陶土信号 | `#E57A3F` |
| `night` | 夜蓝花园 | `#76A5FF` |

- 工作区导航器固定在画布**左上角**：每行显示颜色、名称、素材数、编辑入口；超过 240px 内部滚动；收起状态持久化到快照。
- 双击名称可**快速重命名**；`⤢ 适配` 缩放到该工作区。

### 6.6 底部状态条（五阶段）

`STAGES = ['素材配方', '视觉风格', '需求说明', '需求拆解', '生成产物']`（`index.html:2229`）。

只展示**当前工作区**的阶段进度；生成开始后切换为**真实 Recipe Run 与阶段耗时**。
移动端只保留阶段点，隐藏长标签。

---

## 7. 版本迭代（反馈循环）

在产物节点的检查器里用自然语言提反馈，走：

```js
POST /api/feedback
```

后端 `pipeline.run_feedback` 的行为：

1. 解析口语反馈 → 抽 `tokens` 修改 + 命中规则列表。
2. 重渲染 `output.html`。
3. 把新版本写入 **`revisions/rev<N>.html`**（`pipeline.py:398`）。
4. 更新 `.foxstate.json`（`pipeline.py:406`）与 `feedback.md`（`pipeline.py:409`）。

CLI 等价物：

```bash
htmlninefox feedback --project <项目> --note "<反馈>" --dry-run   # 只看解析
htmlninefox feedback --project <项目> --note "<反馈>"             # 真改写
```

**关键点**：`.foxstate.json` 记录模板、页面区块、附件、Skill 和选择模式，
所以后续反馈迭代是**基于确定状态改写**，不是重新猜测。

---

## 8. 常用 REST 接口（画布背后的 API）

`htmlninefox/server/app.py`：

| 方法 | 路径 | 用途 | 行号 |
|---|---|---|---|
| GET | `/api/health` | 就绪探针（启动后打开浏览器靠它） | 270 |
| GET | `/api/capabilities` | 能力清单 | 274 |
| GET | `/api/exports/capabilities` | 导出能力（格式/纸张/倍率） | 276 |
| GET | `/api/templates` | 模板库 | 278 |
| GET | `/api/template-preview?intent=&template=` | 模板预览 HTML | 319 |
| GET | `/api/gallery` | 私人模板资产库 | 280 |
| GET | `/api/alliance` | 联盟 Skill 列表 | 327 |
| GET/PUT/DELETE | `/api/memory` | Project Memory 读 / 写 / 清空 | 317 / 438 / 461 |
| GET/PUT | `/api/settings/ai` | AI 配置（只回 `api_key_set`，不回明文） | 315 / 444 |
| POST | `/api/settings/ai/test` | 连接测试 | 383 |
| POST | `/api/analyze` | 需求拆解 | 363 |
| POST | `/api/inputs` | 附件上传 | 367 |
| POST | `/api/gallery/import` | 私人模板导入 | 373 |
| GET/POST | `/api/jobs` | 异步任务查询 / 提交 | 332 / 392 |
| DELETE | `/api/jobs/<id>` | 取消任务 | 463 |
| GET/POST | `/api/projects` | 项目列表 / 操作 | 330 |
| GET/DELETE/PATCH | `/api/projects/<name>` | 项目读取 / 删除 / 重命名 | 338 / 465 / 454 |
| POST | `/api/projects/<name>/recipe-rerun` | 局部重跑 Generate / Verify | 409 |
| POST | `/api/projects/<name>/adopt` | **采用此版本并学习** | 421 |
| POST | `/api/projects/<name>/duplicate` | 复制项目 | 429 |
| POST | `/api/generate` | 同步生成 | 361 |
| POST | `/api/feedback` | 反馈迭代 | 365 |
| GET/POST | `/api/exports/analyze` \| `/api/exports` | 导出预检 / 执行 | 394 / 399 |
| POST | `/api/diagnostics` | 诊断包 | 406 |
| GET | `/api/workspace` | 工作区快照 | 336 |

---

## 9. Agent 实操顺序（照着做）

```text
1. htmlninefox workbench                # 起工作台
2. 打开 http://127.0.0.1:8620
3. 点顶部「＋ 输入需求」→ 填文字 / 传文件图片 → 「输入 → AI 分析 → 推荐组合 → 生成」
4. 两条路：
   A. 采用推荐  → 系统自动把模板与页面配方放进工作区并生成
   B. 自定义    → 需求与附件先进工作区，再从「版式/内容/风格/文件/技能」自由组合
5. 点工作区 ▶ 推进 → 看拆解结果 → 生成产物节点
6. 产物检查器：预览 / 反馈迭代 / 局部重跑 / 导出中心 / 采用此版本并学习
7. 反馈不满意 → 自然语言提反馈 → rev2 / rev3 … 继续迭代
```

**排查提示**：

- 推进时报「请先点顶部输入需求」→ 工作区里没有需求节点，或需求文字为空且无附件。
- 拆解意图与所选版式不符 → 检查需求文字里的类型关键词；`intent_confidence ≥ 0.55` 时需求优先。
- 预览空白 → 确认 `GET /api/health` 200，且没有把 `8620` 暴露到不可信网络。
- 生成后标题不可读 → 点「适配全部」（自动适配最低缩放 30%，并给工作区导航器留位）。

---

> **GitHub**：<https://github.com/KratosLee-6/Html-ninefox>
> **小红书搜 KratosLee 看演示**
