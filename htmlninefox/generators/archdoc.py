"""archdoc.py · 架构文档生成器（技术方案/架构图页）

区块：title → layer_diagram → flow → component_table → decisions
分层图与流程图用纯 CSS（无 SVG 依赖），可直接进评审。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
.doc { max-width:960px; margin:0 auto; padding:56px 32px 80px; }
.doc-head { border-bottom:2px solid var(--fox-text); padding-bottom:24px; margin-bottom:40px; }
.doc-head .meta { color:var(--fox-muted); font-size:.85rem; margin-top:10px;
  display:flex; gap:18px; flex-wrap:wrap; }
.doc h1 { font-size:2.1rem; letter-spacing:-.01em; }
.doc h2 { font-size:1.35rem; margin:44px 0 18px; display:flex; align-items:center; gap:12px; }
.doc h2 .idx { color:var(--fox-primary); font-size:.85rem; font-weight:800;
  letter-spacing:.1em; }
.layers { display:grid; gap:12px; margin:22px 0; }
.layer { display:flex; align-items:center; gap:18px; padding:18px 22px; }
.layer .name { font-weight:800; width:130px; flex:none; }
.layer .desc { color:var(--fox-muted); font-size:.92rem; }
.layer .chips { margin-left:auto; display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.chip { font-size:.75rem; padding:3px 10px; border-radius:999px;
  background:color-mix(in srgb, var(--fox-primary) 12%, transparent); color:var(--fox-primary);
  font-weight:600; white-space:nowrap; }
.layer.core { border-left:4px solid var(--fox-primary); }
.layer.allied { border-left:4px solid var(--fox-accent); }
.flow { display:flex; align-items:stretch; gap:0; margin:24px 0 10px; flex-wrap:wrap; }
.fnode { flex:1; min-width:130px; padding:16px 14px; text-align:center; position:relative; }
.fnode .t { font-weight:700; font-size:.92rem; }
.fnode .d { color:var(--fox-muted); font-size:.78rem; margin-top:4px; }
.fnode:not(:last-child)::after { content:'→'; position:absolute; right:-13px; top:50%;
  transform:translateY(-50%); color:var(--fox-primary); font-weight:800; z-index:1; }
.gap-arrow { flex:none; width:26px; }
table.spec { width:100%; border-collapse:collapse; font-size:.9rem; margin-top:8px; }
table.spec th { text-align:left; padding:10px 14px; color:var(--fox-muted); font-weight:600;
  border-bottom:2px solid var(--fox-border); font-size:.8rem; letter-spacing:.05em; }
table.spec td { padding:12px 14px; border-bottom:1px solid var(--fox-border);
  vertical-align:top; }
table.spec td:first-child { font-weight:700; white-space:nowrap; }
.decision { padding:20px 24px; margin-bottom:12px; }
.decision h4 { font-size:1rem; margin-bottom:6px; }
.decision p { color:var(--fox-muted); font-size:.92rem; }
.badge { display:inline-block; font-size:.72rem; padding:2px 10px; border-radius:999px;
  font-weight:700; margin-left:8px; vertical-align:2px; }
.badge.own { background:color-mix(in srgb, var(--fox-primary) 14%, transparent);
  color:var(--fox-primary); }
.badge.allied { background:color-mix(in srgb, var(--fox-accent) 14%, transparent);
  color:var(--fox-accent); }
.note { color:var(--fox-muted); font-size:.85rem; margin-top:10px; }
"""

_LAYERS = [
    ("入口层", "CLI / Web 工作台 / Claude Code Skill 三端统一走同一流水线", ["CLI", "Serve", "SKILL.md"], "allied"),
    ("编排层", "5 专家流水线：Brief → Style → Asset → Generate → Feedback", ["Pipeline"], "core"),
    ("联盟层", "意图路由到联盟 skill，未安装则本地生成器兜底", ["guizang-ppt", "huashu-design", "archify"], "allied"),
    ("沉淀层", "Brief 库 / 审美模板库 / 反馈库，本地文件 + git 可分享", ["~/.htmlninefox/"], "core"),
    ("模型层", "LiteLLM 多模型路由 + 磁盘缓存 + 成本追踪；离线规则引擎兜底", ["LiteLLM", "Rules"], "core"),
]

_FLOW = [
    ("用户需求", "一句话 Brief"),
    ("Brief Expert", "结构化五字段"),
    ("Style Expert", "token 决策"),
    ("Asset Expert", "区块规划"),
    ("Generate", "单文件 HTML"),
    ("Feedback", "token 迭代"),
]

_COMPONENTS = [
    ("rules.py", "离线规则引擎", "意图分类 / Brief 抽取 / 反馈解析，无 LLM 可用", "自研"),
    ("brief_expert", "Brief 专家", "LLM 优先 + 规则兜底，输出 Brief 标准 v0.1 JSON", "自研·核心"),
    ("style_expert", "风格专家", "6 风格预设 × token 匹配，LLM 增强", "自研·核心"),
    ("asset_expert", "资产专家", "按内容类型规划区块与图表数据", "自研"),
    ("generate_expert", "生成专家", "5 类内容生成器，CSS 变量驱动", "自研·核心"),
    ("feedback_expert", "反馈专家", "口语反馈 → token 变更 → 重渲染", "自研·核心"),
    ("alliance/router", "联盟路由", "skill-manifest.yaml 协议 + 本地 fallback", "联盟"),
    ("server/", "Web 端", "stdlib http.server REST API + 工作台", "自研"),
]

_DECISIONS = [
    ("为什么生成器不用 React/构建链？", "单文件 HTML 零依赖可发布——双击即开，符合「能交付的 HTML」定位。"),
    ("为什么 LLM 是可选依赖？", "0 资金原则：离线规则引擎保证无 Key 可用，有 Key 时体验增强而非必需。"),
    ("为什么反馈走 token 而非改 DOM？", "改 token → 重渲染 = 沉淀可复用审美模板；改 DOM = 一次性修补。"),
]


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    core = content_of(brief, "core_message", "系统架构与关键决策")
    blocks = blocks_of(assets) or ["title", "layer_diagram", "flow", "component_table", "decisions"]

    parts = ['<main class="doc">']
    if "title" in blocks:
        parts.append(f"""
<header class="doc-head">
  <h1>{esc(brand)} · {esc(content_of(brief, "headline", core))}</h1>
  <div class="meta"><span>版本 v0.2</span><span>2026-08-29</span>
    <span>状态：评审稿</span><span>作者：Html九尾狐 生成</span></div>
</header>""")

    if "layer_diagram" in blocks:
        layers = "".join(f"""
  <div class="layer card {cls}">
    <span class="name">{esc(name)}</span>
    <span class="desc">{esc(desc)}</span>
    <span class="chips">{''.join(f'<span class="chip">{esc(c)}</span>' for c in chips)}</span>
  </div>""" for name, desc, chips, cls in _LAYERS)
        parts.append(f'<h2><span class="idx">01</span>系统分层</h2><div class="layers">{layers}</div>'
                     '<p class="note">实心边 = 自研核心，彩色边 = 联盟/生态。</p>')

    if "flow" in blocks:
        flow = "".join(f"""
    <div class="fnode card"><div class="t">{esc(t)}</div><div class="d">{esc(d)}</div></div>"""
                       for t, d in _FLOW)
        parts.append(f'<h2><span class="idx">02</span>生成流水线</h2><div class="flow">{flow}</div>')

    if "component_table" in blocks:
        rows = "".join(f"""
  <tr><td>{esc(mod)}</td><td>{esc(name)}</td><td>{esc(desc)}</td>
      <td><span class="badge {'own' if '自研' in own else 'allied'}">{esc(own)}</span></td></tr>"""
                       for mod, name, desc, own in _COMPONENTS)
        parts.append(f"""
<h2><span class="idx">03</span>组件清单</h2>
<table class="spec"><thead><tr><th>模块</th><th>名称</th><th>职责</th><th>归属</th></tr></thead>
<tbody>{rows}</tbody></table>""")

    if "decisions" in blocks:
        decs = "".join(f"""
  <div class="decision card"><h4>Q：{esc(q)}</h4><p>{esc(a)}</p></div>"""
                       for q, a in _DECISIONS)
        parts.append(f'<h2><span class="idx">04</span>关键决策</h2>{decs}')

    parts.append("</main>")
    return html_shell(f"{brand} · 架构文档", preset, "\n".join(parts), _EXTRA,
                      generator="htmlninefox-v0.2/archdoc")
