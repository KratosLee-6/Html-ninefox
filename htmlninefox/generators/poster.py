"""poster.py · 海报生成器（单屏大字报）

区块：headline → key_info → details → action_bar
一屏设计（100vh），远距离可读优先。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
.stage { min-height:100vh; display:flex; flex-direction:column;
  padding:clamp(24px,5vw,64px); position:relative; overflow:hidden; }
.stage::before { content:''; position:absolute; width:56vw; height:56vw; border-radius:50%;
  background:radial-gradient(closest-side, color-mix(in srgb, var(--fox-primary) 26%, transparent), transparent);
  top:-18vw; right:-18vw; pointer-events:none; }
.stage::after { content:''; position:absolute; width:40vw; height:40vw; border-radius:50%;
  background:radial-gradient(closest-side, color-mix(in srgb, var(--fox-accent) 18%, transparent), transparent);
  bottom:-14vw; left:-12vw; pointer-events:none; }
.brandline { display:flex; justify-content:space-between; align-items:center;
  font-weight:700; font-size:.95rem; z-index:1; }
.brandline .no { color:var(--fox-muted); font-weight:400; letter-spacing:.15em; }
.headline { margin:auto 0; z-index:1; padding:40px 0; }
.headline .kick { color:var(--fox-accent); font-weight:800; letter-spacing:.3em;
  font-size:clamp(.8rem,1.6vw,1rem); text-transform:uppercase; }
.headline h1 { font-size:clamp(3rem,10vw,7.5rem); line-height:1.06; letter-spacing:-.02em;
  margin:18px 0; }
.headline h1 em { font-style:normal; color:var(--fox-primary); }
.headline .sub { font-size:clamp(1rem,2.4vw,1.4rem); color:var(--fox-muted); max-width:640px; }
.keyinfo { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; z-index:1; }
.ki { padding:20px 22px; backdrop-filter:blur(4px); }
.ki .k { color:var(--fox-muted); font-size:.8rem; letter-spacing:.12em; text-transform:uppercase; }
.ki .v { font-size:clamp(1.05rem,2.4vw,1.5rem); font-weight:800; margin-top:6px; }
.actionbar { display:flex; align-items:center; justify-content:space-between; gap:20px;
  margin-top:20px; padding:22px 26px; z-index:1;
  background:var(--fox-primary); color:var(--fox-primary_text);
  border-radius:var(--fox-radius); flex-wrap:wrap; }
.actionbar .cta { font-size:clamp(1rem,2.2vw,1.3rem); font-weight:800; }
.actionbar .qr { font-size:.85rem; opacity:.85; }
@media (max-width:760px) { .keyinfo { grid-template-columns:1fr; } }
"""


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    core = content_of(brief, "core_message", "一场关于创造力的聚会")
    blocks = blocks_of(assets) or ["headline", "key_info", "details", "action_bar"]

    parts = [f"""
<div class="stage">
  <div class="brandline"><span>🦊 {esc(brand)}</span><span class="no">POSTER / 2026</span></div>"""]

    if "headline" in blocks:
        parts.append(f"""
  <div class="headline">
    <div class="kick">ANNOUNCING</div>
    <h1>{esc(content_of(brief, "headline", core))}</h1>
    <p class="sub">{esc(content_of(brief, "hero_sub", "一次想清楚，长期可复用 —— 邀你共同见证。"))}</p>
  </div>""")

    if "key_info" in blocks or "details" in blocks:
        parts.append(f"""
  <div class="keyinfo">
    <div class="ki card"><div class="k">时间</div><div class="v">2026.09.12 14:00</div></div>
    <div class="ki card"><div class="k">地点</div><div class="v">线上直播 · 免费报名</div></div>
    <div class="ki card"><div class="k">嘉宾</div><div class="v">Skill 联盟三位作者</div></div>
  </div>""")

    if "action_bar" in blocks:
        parts.append(f"""
  <div class="actionbar">
    <span class="cta">立即扫码报名 →</span>
    <span class="qr">{esc(brand.lower())}.dev/live · 席位有限</span>
  </div>
</div>""")

    return html_shell(f"{brand} · 海报", preset, "\n".join(parts), _EXTRA,
                      generator="htmlninefox-v0.2/poster")
