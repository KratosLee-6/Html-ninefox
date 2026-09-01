"""_shared.py · 生成器共享工具：HTML 骨架 + 基础样式（消费 token，不 hardcode 颜色）"""

from __future__ import annotations

import html as _html
from typing import Any, Dict

from ._tokens import css_vars


def esc(text: Any) -> str:
    return _html.escape(str(text), quote=True)


def visual_system_css(preset: Dict[str, Any]) -> str:
    system = preset.get("visual_system", "")
    systems = {
        "pixel-garden": r"""
body { background-image:linear-gradient(rgba(23,60,143,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(23,60,143,.035) 1px,transparent 1px); background-size:12px 12px; }
.hero { max-width:none; padding-left:max(32px,calc((100vw - 1120px)/2 + 32px)); padding-right:max(32px,calc((100vw - 1120px)/2 + 32px)); background:linear-gradient(180deg,#173C8F 0%,#1D5590 58%,#49B894 100%); color:#F8F5EA; border-bottom:6px double #DCE6D2; }
.hero .tag,.hero p.lead { color:#E3EEE5; } .hero .panel { border-radius:4px; background:rgba(7,29,62,.28); }
.hero .panel-inner { min-height:220px; display:grid; place-items:end start; color:#F8F5EA; border-radius:2px; border:2px solid rgba(248,245,234,.28); background:linear-gradient(180deg,rgba(30,109,168,.3),rgba(22,88,79,.8)),repeating-linear-gradient(90deg,transparent 0 18px,rgba(255,255,255,.04) 18px 20px); }
.card { border-width:2px; box-shadow:4px 4px 0 color-mix(in srgb,var(--fox-primary) 12%,transparent); }
""",
        "duotone-studio": r"""
body { background:linear-gradient(145deg,#F8F7F3 0%,#ECEEF0 52%,#F4F2EC 100%); }
.hero { padding-top:120px; } .hero h1 { font-weight:800; letter-spacing:-.055em; }
.hero .panel { padding:18px; background:linear-gradient(135deg,#E1E3E5,#FAFAF7); box-shadow:0 34px 90px rgba(49,55,64,.16); }
.hero .panel-inner { min-height:230px; display:grid; place-items:center; background:linear-gradient(145deg,#FFFFFF,#EFF1F2); box-shadow:inset 0 1px 0 #fff; }
.card { box-shadow:0 12px 34px rgba(47,52,59,.07); } section.block:nth-of-type(even) { background:#25282D; color:#F4F2EC; max-width:none; padding-left:max(32px,calc((100vw - 1120px)/2 + 32px)); padding-right:max(32px,calc((100vw - 1120px)/2 + 32px)); }
section.block:nth-of-type(even) .card { background:#30343A; border-color:#42474E; } section.block:nth-of-type(even) .muted,section.block:nth-of-type(even) p { color:#B9BEC5; }
""",
        "editorial-ink": r"""
body { background:linear-gradient(90deg,transparent 0 7%,rgba(23,25,27,.06) 7% calc(7% + 1px),transparent calc(7% + 1px)); }
.wrap { max-width:1240px; } .nav { border-bottom:1px solid var(--fox-text); }
.hero { text-align:left; padding-top:110px; } .hero h1 { max-width:900px; font-size:clamp(3.2rem,8vw,7.2rem); font-weight:500; line-height:.96; letter-spacing:-.045em; }
.hero p.lead { margin-left:0; } .hero .actions { justify-content:flex-start; } .hero .panel { background:none; border-top:1px solid var(--fox-text); border-radius:0; padding:18px 0 0; }
.card,.btn,.tag,.faq details { border-radius:0; box-shadow:none; } .sec-head { border-top:1px solid var(--fox-text); padding-top:16px; }
""",
        "swiss-signal": r"""
body { background-image:linear-gradient(90deg,rgba(21,22,23,.045) 1px,transparent 1px); background-size:calc(100vw / 16) 100%; }
.wrap { max-width:none; padding-left:4vw; padding-right:4vw; } .nav { border-bottom:1px solid var(--fox-text); }
.hero { text-align:left; min-height:72vh; background:linear-gradient(90deg,var(--fox-primary) 0 38%,transparent 38%); display:grid; align-content:center; padding-left:42%; }
.hero h1 { font-size:clamp(3.5rem,8vw,8rem); line-height:.86; text-transform:uppercase; font-weight:900; letter-spacing:-.065em; }
.hero p.lead { margin-left:0; } .hero .actions { justify-content:flex-start; } .hero .panel { display:none; }
.card,.btn,.tag,.faq details { border-radius:0; box-shadow:none; } .grid3,.pricing { gap:0; border-top:1px solid var(--fox-text); border-left:1px solid var(--fox-text); } .grid3 .card,.pricing .card { border-width:0 1px 1px 0; }
""",
        "soft-silver": r"""
body { background:radial-gradient(circle at 18% 4%,rgba(255,255,255,.95),transparent 28%),radial-gradient(circle at 82% 18%,rgba(64,125,112,.14),transparent 32%),linear-gradient(145deg,#ECEDEA,#DDE1DE); }
.nav { margin-top:18px; padding:14px 18px; border:1px solid rgba(255,255,255,.7); background:rgba(248,248,245,.72); border-radius:22px; backdrop-filter:blur(18px); box-shadow:0 20px 60px rgba(43,51,48,.1); }
.hero h1 { font-weight:760; letter-spacing:-.05em; } .hero .panel { padding:10px; border:1px solid rgba(255,255,255,.9); box-shadow:0 30px 80px rgba(56,66,63,.15); }
.hero .panel-inner,.card { box-shadow:inset 0 1px 0 rgba(255,255,255,.9),0 16px 42px rgba(56,66,63,.08); }
.btn { box-shadow:inset 0 1px 0 rgba(255,255,255,.25),0 8px 22px rgba(64,125,112,.2); }
""",
    }
    return systems.get(system, "")


def base_css(preset: Dict[str, Any], extra: str = "") -> str:
    t = preset["tokens"]
    font_scale = float(t.get("_font_scale", 1.0))
    font_base = t.get("_font_base", "16px")
    if font_base.endswith("px"):
        font_base = f"{float(font_base[:-2]) * font_scale:.1f}px"
    return f"""
:root {{
{css_vars({k: v for k, v in t.items() if not k.startswith('_')})}
  --fox-font-base: {font_base};
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: var(--fox-font_body);
  font-size: var(--fox-font-base);
  line-height: 1.7;
  background: var(--fox-bg);
  color: var(--fox-text);
  -webkit-font-smoothing: antialiased;
}}
h1, h2, h3, h4 {{ font-family: var(--fox-font_display); line-height: 1.25; }}
a {{ color: var(--fox-accent); text-decoration: none; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 0 32px; }}
.card {{
  background: var(--fox-surface);
  border: 1px solid var(--fox-border);
  border-radius: var(--fox-radius);
}}
.btn {{
  display: inline-block; padding: 12px 28px; border-radius: var(--fox-radius);
  background: var(--fox-primary); color: var(--fox-primary_text);
  font-weight: 600; border: none; cursor: pointer; font-size: 1rem;
}}
.btn.ghost {{
  background: transparent; color: var(--fox-text);
  border: 1px solid var(--fox-border);
}}
.tag {{
  display: inline-block; padding: 4px 12px; font-size: .8rem; border-radius: 999px;
  background: color-mix(in srgb, var(--fox-primary) 14%, transparent);
  color: var(--fox-primary); font-weight: 600; letter-spacing: .04em;
}}
.muted {{ color: var(--fox-muted); }}
{extra}
{visual_system_css(preset)}
"""


def html_shell(title: str, preset: Dict[str, Any], body: str, extra_css: str = "",
               body_attrs: str = "", generator: str = "htmlninefox-v0.2") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{esc(generator)}">
<title>{esc(title)}</title>
<style>{base_css(preset, extra_css)}</style>
</head>
<body{body_attrs}>
{body}
</body>
</html>"""


def content_of(brief: dict, key: str, default: str = "") -> str:
    """从 brief（兼容嵌套/扁平）取 content 字段。"""
    payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
    c = payload.get("content", {}) or {}
    return str(c.get(key) or default)


def blocks_of(assets: dict) -> list:
    """资产规划的区块列表（asset_expert 输出），兜底空。"""
    if not isinstance(assets, dict):
        return []
    return list(assets.get("blocks") or [])


def brand_of(brief: dict) -> str:
    return content_of(brief, "brand", "Your Product") or "Your Product"
