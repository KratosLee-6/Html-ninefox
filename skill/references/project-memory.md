# 🧠 Project Memory · v0.5 记忆系统

> 出处：`htmlninefox/project_memory.py`、`docs/CONTEXT.md`、`docs/RELEASE-NOTES-v0.5.0rc1.md`、`docs/INTERACTION-SYSTEM-v0.5.md`
> 引入版本：v0.5.0rc1 · 目标：**「越用越懂你」的本地复利闭环**

---

## 1. 核心设计原则（先读这段）

> **系统不会自动把每次生成都当成正确答案。**

只有用户在**产物检查器**里**明确点击「♡ 采用此版本并学习」**，
这个项目的偏好才会进入长期记忆。
**测试稿和失败稿不会污染偏好。**

三个必须记住的优先级与边界：

| 规则 | 含义 |
|---|---|
| **Explicit Requirement > Project Memory** | 本次需求里明确说的品牌 / 受众 / 语气 / 禁忌 / 模板 / 颜色 / 字体，**永远覆盖**长期记忆 |
| **采用信号才写入** | 没有 adoption signal，记忆不会被修改 |
| **可解释复用** | 每次分析、Recipe Run、产物检查器都会显示「复用了什么」和「哪些被本次覆盖」 |

### 领域术语（`docs/CONTEXT.md`）

- **Project**：包含源状态、HTML 产物、反馈与运行证据的本地创作单元。
- **Recipe Run**：一次可追踪、可恢复的创作执行（分析 / 组合 / 生成 / 验证 / 交付五阶段）。
- **Project Memory**：用户明确采用产物后形成的长期偏好与项目知识。
- **Adoption Signal**：用户确认某个产物值得后续复用的明确行为。
- **Memory Recommendation**：一次生成中从 Project Memory 匹配出的建议及其解释。
- **Explicit Requirement**：本次需求中用户明确提出的约束，**优先级始终高于 Project Memory**。

---

## 2. 存在哪里

```text
<输出根目录>/.settings/project-memory.json
```

- 由 `output_root` 决定（`ProjectMemoryStore.__init__`，`project_memory.py:79-81`）。
- 默认 `output_root` 就是 `~/htmlninefox-output`。
- **纯本地**：不上传、不进项目快照、不进诊断包、不进 Git。

### 2.1 写入是原子的

`_write()`（`project_memory.py:259-263`）先写 `<name>.tmp`，再 `replace()` 覆盖正式文件 ——
避免 Windows 上高频轮询时读到半截 JSON。
另外全程有 `threading.RLock` 保护（`project_memory.py:65-73`）。

### 2.2 读取是容错的

`read()`（`project_memory.py:83-91`）在以下情况**静默回退到默认空记忆**，不抛异常：

- 文件不存在
- JSON 解析失败（`JSONDecodeError`）
- 类型 / 取值异常（`ValueError` / `TypeError`）
- I/O 失败（`OSError`）

→ 记忆文件坏掉**不会阻塞生成**，这是刻意的设计。

---

## 3. 数据结构（完整字段）

`_default_memory()`（`project_memory.py:30-41`）：

```json
{
  "version": 1,
  "enabled": true,
  "profile": {
    "brand": "",
    "audience": "",
    "tone": "",
    "forbidden": [],
    "preferred_preset_by_intent": {},
    "preferred_primary": "",
    "preferred_font": "",
    "notes": ""
  },
  "stats": {
    "adopted_count": 0,
    "generated_with_memory": 0,
    "last_adopted_project": ""
  },
  "evidence": [],
  "decisions": [],
  "updated_at": ""
}
```

### 3.1 `profile` 字段说明

| 字段 | 类型 | 上限 | 什么时候被写入 |
|---|---|---|---|
| `brand` | 字符串 | 500 字符 | adopt 时取 `brief.content.brand` |
| `audience` | 字符串 | 500 | adopt 时取 `brief.goal.audience` |
| `tone` | 字符串 | 160 | adopt 时取 `brief.style.tone` |
| `forbidden` | 字符串数组 | **24 项**，单项 160 | adopt 时取 `brief.constraints.forbidden`，与已有**合并去重** |
| `preferred_preset_by_intent` | 映射 | 16 键，键 40 字符 / 值 80 字符 | adopt 时 `[intent] = preset_id` |
| `preferred_primary` | 形如 `#RRGGBB` | 20 | adopt 时取 `preset.tokens.primary`，**必须匹配 `^#[0-9A-Fa-f]{6}$`**，存大写 |
| `preferred_font` | `serif` / `sans` / `mono` | 20 | adopt 时从 `tokens.font_body` 或 `font_display` 归一化 |
| `notes` | 字符串 | **2000 字符** | 仅手动编辑 |

### 3.2 字体归一化规则（`_font_key`，`project_memory.py:275-284`）

| 输入包含 | 归一到 |
|---|---|
| `mono` / `consolas` | `mono` |
| `sans-serif` / `pingfang` / `yahei` / `inter` | `sans` |
| `serif` / `songti` / `simsun` | `serif` |
| 其他非空 | `sans` |

### 3.3 `stats`

| 字段 | 含义 |
|---|---|
| `adopted_count` | 累计**被采用**的产物数 |
| `generated_with_memory` | 复用记忆生成的次数（仅当本次确实有 `applied` 项才 +1） |
| `last_adopted_project` | 最近采用的项目名 |

工作台记忆弹窗顶部三个数字就是它们（`已采用产物` / `复用记忆生成` / `最近采用项目`）。

### 3.4 `evidence`（最多 30 条）

`_safe_evidence`（`project_memory.py:293-298`）：

```json
{ "project": "html9n-2026-09-16-101500", "intent": "landing",
  "preset_id": "fox-pixel-garden", "revision": 2,
  "adopted_at": "2026-09-16T10:20:33" }
```

用途：**采纳轨迹**。也是**幂等判据**——同一个项目名再次 adopt 会直接返回「已采用」。

### 3.5 `decisions`（最多 30 条）

`_safe_decision`（`project_memory.py:300-304`）：

```json
{ "project": "...", "suggestion": "≤300 字的设计决策摘要",
  "rules": ["…"], "tokens": { "primary": "#173C8F", "font_body": "…" },
  "adopted_at": "..." }
```

`tokens` 只保留**白名单 6 键**（`_safe_tokens`，`project_memory.py:286-291`）：

```text
primary · background · surface · text · font_body · font_display
```

其他键一律丢弃。

### 3.6 体积上限

```text
MAX_MEMORY_BYTES = 128 * 1024   # 128KB
```

归一化后若序列化超过 128KB，直接抛 `ValueError("项目记忆超过 128KB")`（`project_memory.py:255-256`），**不写入**。

---

## 4. 什么时候写入（三个入口）

### 4.1 采用（Adoption） — 唯一的长期学习入口

**UI**：产物检查器底部按钮（`index.html:1955`）

```text
♡ 采用此版本并学习      ← 未采用时（btn-primary，可点）
✓ 已采用并学习          ← 已采用时（btn-secondary，disabled）
```

**API**：

```http
POST /api/projects/<name>/adopt
```

**CLI 场景**：目前 adopt 只在工作台 / HTTP API 暴露（CLI 无 adopt 子命令）。

`adopt()` 的完整流程（`project_memory.py:157-220`）：

```text
1. 项目必须在 output_root 内          → 否则 ValueError「项目不在当前输出目录」
2. 必须存在 .foxstate.json            → 否则 ValueError「项目缺少 .foxstate.json」
3. 幂等检查：evidence 里已有同名项目   → 返回 {adopted: false, already_adopted: true}
4. 从 .foxstate.json 提取 brief / preset / intent / tokens / last_feedback
5. learn 六个字段（brand/audience/tone/forbidden/模板/主色/字体）
6. 追加一条 decision（front，最多 30）
7. 追加一条 evidence（front，最多 30）
8. stats.adopted_count += 1；stats.last_adopted_project = 项目名
9. 更新 updated_at → 归一化 → 原子写入
10. 返回 { adopted: true, learned: [ {field, value} … ] }
```

**只有非空值才会被 learn**（`learn()` 里 `if value in (None, "", []): return`）。

### 4.2 生成时复用（只更新计数，不改 profile）

`recommend()` 被调用后，若本次确实应用了记忆项，
`record_generation()` 把 `stats.generated_with_memory` +1（`project_memory.py:222-230`）。

**注意**：生成**永远不会**改写 `profile`。学习只能靠 adopt。

### 4.3 手动编辑

工作台「项目记忆」弹窗可直接改 `profile` 各字段、切换开关、清空。
底层走 `save(payload)`（`project_memory.py:93-107`）：
`enabled` 与 `profile` 做**增量 merge**（不是整体替换），然后统一归一化写盘。

---

## 5. 复用决策逻辑（recommend）

`recommend(prompt, request)`（`project_memory.py:116-155`）返回：

```json
{ "enabled": true, "intent": "landing",
  "applied": [ { "field": "brand", "value": "狐构" } ],
  "covered": [ { "field": "tone", "reason": "本次明确要求优先" } ],
  "values": { "brand": "狐构", "tone": "克制" },
  "overrides": { "template": "fox-pixel-garden", "primary": "#173C8F", "font": "sans" } }
```

- `enabled == false` → 全空返回，等价关闭（`project_memory.py:121-122`）。
- `applied` = 本次**实际复用了**的记忆项（要展示给用户看）。
- `covered` = 记忆里有、但被**本次明确要求/选择**盖掉的项。
- `overrides` 只含 `template` / `primary` / `font` 三个可注入下一阶段的键。

### 5.1 「本次明确要求」怎么判定（`_explicit_requirements`，`project_memory.py:265-273`）

| 字段 | 判定依据 |
|---|---|
| `brand` | `rules.detect_brand(text)` 命中，或 `request.brand` 有值 |
| `audience` | `rules.detect_audience(text)` 有匹配，或 `request.audience` 有值 |
| `tone` | `rules.detect_tone(text)` 有匹配，或 `request.tone` 有值 |
| `forbidden` | 文本命中 `不要` / `避免` / `禁止` / `禁用` / `不能` / `不可` / `排除` |

### 5.2 模板 / 主色 / 字体的覆盖判定（`project_memory.py:139-153`）

- `intent` = `request.intent`，缺省用 `rules.classify_intent(prompt)[0]`。
- 模板来自 `profile.preferred_preset_by_intent[intent]`。
- 若 `request` 里给了同名键（模板还额外认 `gallery_id`）→ 记入 `covered`，理由 **「本次明确选择优先」**。
- 否则写入 `overrides`，记入 `applied`。

**所以**：用户这次指定了模板 / 色卡 / 字体，就**不会**被记忆里的偏好覆盖。

---

## 6. 隐私边界（重要的「不写什么」）

官方明确的排除项：

```text
❌ API Key
❌ 附件正文
❌ 完整反馈原文
✅ 只保存受控字段 + 设计决策摘要
```

具体落地：

| 项 | 处理方式 |
|---|---|
| API Key | 存在**另一个文件** `<output_root>/.settings/ai.json`；接口只回 `api_key_set: true/false`，**永不回明文**；不进项目快照 / 诊断包 / Git |
| 附件 / 文件 / 图片 | 存本地 `<output_root>/.inputs/`（单文件默认上限 8MB）；**正文不进记忆** |
| 反馈原文 | `decisions.suggestion` 只截 **≤300 字符**摘要；完整反馈留在项目 `feedback.md` |
| Token | 只白名单 6 键；`_text(item, 160)` 截断 |
| 列表 | `forbidden` ≤ 24 项；`evidence` / `decisions` ≤ 30 条 |
| 项目范围 | `adopt` 要求项目必须在 `output_root` 内（`relative_to` 校验），**拒绝越界路径** |

设计意图：**单机、本地、可解释的结构化记忆**。
（多人记忆隔离、常用素材语义检索属于 RC2 范围，目前没有。）

---

## 7. 怎么查看 / 编辑 / 关闭 / 清空

### 7.1 工作台内（推荐）

**产物节点检查器 → 「采用此版本并学习」旁边的记忆入口**，打开「项目记忆」弹窗：

- 顶部三个统计：**已采用产物 / 复用记忆生成 / 最近采用项目**。
- 中部编辑 `brand` / `audience` / `tone` / `forbidden` / `notes` 等字段。
- `enabled` 开关：**关闭后本次生成完全不读记忆**。
- 底部危险区：**清空记忆**（二次确认）。

### 7.2 HTTP API

```bash
# 读取
curl -s http://127.0.0.1:8620/api/memory

# 写入（增量 merge）
curl -s -X PUT http://127.0.0.1:8620/api/memory \
  -H "Content-Type: application/json" \
  -d '{"enabled":true,"profile":{"brand":"狐构","tone":"克制、清楚","forbidden":["紫色渐变","机器人头像"],"preferred_primary":"#173C8F"}}'

# 清空
curl -s -X DELETE http://127.0.0.1:8620/api/memory

# 采用某个项目（触发学习）
curl -s -X POST http://127.0.0.1:8620/api/projects/html9n-2026-09-16-101500/adopt
```

`PUT` 的错误码：记忆格式非法 → `project_memory_invalid` (400)。
项目越界 / 缺 `.foxstate.json` → 对应 `ValueError` 文案。

### 7.3 直接读文件

```bash
cat ~/htmlninefox-output/.settings/project-memory.json
```

想彻底重置（不动其他设置）：

```bash
rm ~/htmlninefox-output/.settings/project-memory.json
# 下次 read() 会返回默认空记忆
```

---

## 8. 可解释复用：在哪里看到

| 位置 | 展示内容 |
|---|---|
| 需求分析结果 | 本次复用项与覆盖项 |
| Recipe Run 的 **Analyze** 阶段 | `memory_applied` / `memory_covered` |
| Recipe Run 的 **Compose** 阶段 | `memory_overrides`（实际注入的 template / primary / font） |
| 产物检查器 | 复用解释 + 「本次明确要求覆盖了哪些记忆」 |
| 产物状态 | 持久化 `memory_applied` |
| 记忆弹窗 | 统计数字 + 已采用过哪些项目 |

对应实现：`run_expert` 里 Analyze / Compose 阶段的 `memory_applied` / `memory_covered` / `memory_overrides` 字段（`pipeline.py:139-146`、`pipeline.py:186-193`）。

---

## 9. Agent 实操清单

```text
□ 想让九尾狐"越用越懂用户" → 每次满意产出后，用它打开产物检查器点「♡ 采用此版本并学习」
□ 用户说"这次要深色 / 换品牌" → 本次需求优先，不用先改记忆
□ 用户说"以后都用这个模板" → 采用一次对应 intent 的产物，或直接编辑 preferred_preset_by_intent
□ 用户说"别记我的东西了" → 记忆弹窗关 enabled，或 DELETE /api/memory
□ 记忆疑似污染（错误偏好被复用）→ 看 evidence 找出被采用的项目名，清空后重新采用正确的那一个
□ 需要审计"AI 到底记住了什么" → 直接 cat <output>/.settings/project-memory.json
□ 越界报错「项目不在当前输出目录」→ 项目必须位于工作台 output_root 下才能被 adopt
```

**RC1 边界（别承诺更多）**：
常用素材语义检索、多人记忆隔离、100 节点性能、产物版本差异、完整无障碍发布门禁 → **RC2**。

---

> **GitHub**：<https://github.com/KratosLee-6/Html-ninefox>
> **小红书搜 KratosLee 看演示**
