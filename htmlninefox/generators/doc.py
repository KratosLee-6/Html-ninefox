"""doc.py · 通用文档生成器（报告/方案/纪要/白皮书——以 HTML 为载体的文档）

区块：title → summary → sections → key_points → table → conclusion
与 archdoc（架构技术文档）互补：doc 面向商务/汇报文档。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
.doc { max-width:860px; margin:0 auto; padding:60px 40px 90px; }
.doc-head { text-align:center; padding:20px 0 34px; border-bottom:3px double var(--fox-border);
  margin-bottom:36px; }
.doc-head .tag { margin-bottom:14px; }
.doc-head h1 { font-size:2rem; letter-spacing:-.01em; margin-bottom:12px; }
.doc-head .meta { color:var(--fox-muted); font-size:.85rem; display:flex; gap:16px;
  justify-content:center; flex-wrap:wrap; }
.summary { padding:24px 28px; border-left:4px solid var(--fox-primary); margin-bottom:44px; }
.summary h2 { font-size:1rem; margin-bottom:8px; color:var(--fox-primary); }
.summary p { color:var(--fox-muted); }
section.sec { margin-bottom:40px; }
section.sec h2 { font-size:1.3rem; margin-bottom:14px; padding-left:14px;
  border-left:4px solid var(--fox-primary); }
section.sec p { color:var(--fox-muted); margin-bottom:10px; }
section.sec ul { list-style:none; }
section.sec li { padding:6px 0 6px 26px; position:relative; color:var(--fox-muted); }
section.sec li::before { content:'▪'; position:absolute; left:6px; color:var(--fox-primary); }
.kps { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:18px 0 44px; }
.kp { padding:20px; text-align:center; }
.kp .v { font-size:1.7rem; font-weight:800; color:var(--fox-primary); }
.kp .l { color:var(--fox-muted); font-size:.85rem; margin-top:4px; }
table.tb { width:100%; border-collapse:collapse; font-size:.9rem; margin:12px 0 44px; }
table.tb th { text-align:left; padding:10px 14px; color:var(--fox-muted); font-weight:600;
  border-bottom:2px solid var(--fox-border); font-size:.8rem; }
table.tb td { padding:11px 14px; border-bottom:1px solid var(--fox-border); }
table.tb td:first-child { font-weight:600; }
.conclusion { padding:28px 30px; background:color-mix(in srgb, var(--fox-primary) 7%, var(--fox-surface));
  border:1px solid var(--fox-border); border-radius:var(--fox-radius); }
.conclusion h2 { font-size:1.1rem; margin-bottom:10px; }
.conclusion p { color:var(--fox-muted); }
.sign { display:flex; justify-content:space-between; margin-top:60px; padding-top:20px;
  border-top:1px solid var(--fox-border); color:var(--fox-muted); font-size:.85rem; }
@media (max-width:760px) { .kps { grid-template-columns:1fr; } }
"""


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    headline = content_of(brief, "headline", "项目说明文档")
    blocks = blocks_of(assets) or ["title", "summary", "sections", "key_points", "table", "conclusion"]

    parts = ['<main class="doc">']
    if "title" in blocks:
        parts.append(f"""
<header class="doc-head">
  <span class="tag">DOCUMENT</span>
  <h1>{esc(brand)} · {esc(headline)}</h1>
  <div class="meta"><span>版本 v1.0</span><span>2026-08</span><span>Html九尾狐 编排生成</span></div>
</header>""")

    if "summary" in blocks:
        parts.append(f"""
<div class="summary card"><h2>摘要</h2>
<p>{esc(content_of(brief, "hero_sub", "本文档说明项目的背景、要点与结论，供相关方评审与执行。"))}</p></div>""")

    if "sections" in blocks:
        secs = "".join(f"""
<section class="sec"><h2>{esc(t)}</h2><p>{esc(d)}</p>
<ul><li>{esc(a)}</li><li>{esc(b2)}</li></ul></section>"""
                       for t, d, a, b2 in [
                           ("背景与目标", "说明项目发起的背景与要达成的目标。", "现状与痛点已确认", "目标可量化、可验收"),
                           ("方案与路径", "给出整体思路与分阶段实施路径。", "分三阶段推进，里程碑明确", "每阶段有明确交付物"),
                           ("风险与对策", "列出主要风险与对应预案。", "识别高风险项并指派负责人", "设置检查点与回退方案")])
        parts.append(secs)

    if "key_points" in blocks:
        kps = "".join(f'<div class="kp card"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>'
                      for v, l in [("3 阶段", "实施路径"), ("8 周", "整体周期"), ("5 项", "关键交付物")])
        parts.append(f'<h2 style="font-size:1.3rem;margin-bottom:4px">关键数字</h2><div class="kps">{kps}</div>')

    if "table" in blocks:
        rows = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b2)}</td><td>{esc(c)}</td></tr>"
                       for a, b2, c in [
                           ("阶段一 · 现状调研", "第 1-2 周", "调研报告"),
                           ("阶段二 · 方案落地", "第 3-6 周", "可用系统/文档"),
                           ("阶段三 · 评审交付", "第 7-8 周", "评审结论与验收单")])
        parts.append(f"""
<h2 style="font-size:1.3rem">里程碑计划</h2>
<table class="tb"><thead><tr><th>阶段</th><th>周期</th><th>交付物</th></tr></thead>
<tbody>{rows}</tbody></table>""")

    if "conclusion" in blocks:
        parts.append(f"""
<div class="conclusion"><h2>结论与下一步</h2>
<p>{esc(content_of(brief, "cta_sub", "综上，建议按本方案推进；下一步确认资源与排期，启动阶段一。"))}</p></div>
<div class="sign"><span>{esc(brand)}</span><span>编制：Html九尾狐 · 2026-08</span></div>""")

    parts.append("</main>")
    return html_shell(f"{brand} · {headline}", preset, "\n".join(parts), _EXTRA,
                      generator="htmlninefox-v0.2/doc")
