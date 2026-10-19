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
{ambient_motion_css(preset)}
{extra}
{visual_system_css(preset)}
"""


def ambient_motion_css(preset: Dict[str, Any]) -> str:
    """「墨水落纸」动效层（六类渲染器共享）。

    thesis 来自 Pixel Garden 世界观本身：暖纸、方格、钴蓝与薄荷光。
    生成页不再是静态截图——

      1. 光带呼吸：两团钴蓝/薄荷径向渐变在纸面上缓慢漂移（focal
         moment 的环境部分；只动 background-position，不触发 layout）；
      2. 墨水标题：hero 主标题一次性落纸（translateY + blur 淡入，
         700ms，impeccable 的 focal entrance 档）；
      3. 卡片显形：滚动进入视口时按同级次序 stagger（cap 360ms）；
      4. 光标辉光：仅 (pointer:fine) 下，光标带着一团薄荷微光——
         「你的光标在纸上留下光」（借 shaders 的 spotlight 语言，
         CSS 变量 + 单层渐变实现，无依赖）；
      5. 键盘焦点环（a11y 审计的缺口补齐）。

    prefers-reduced-motion：不做 0.01ms 全杀——所有元素直接以终态
    静态呈现（状态变化与层级完整保留，符合 impeccable 审计对
    motion sensitivity 的要求）。JS 侧由 ambient_motion_js 配合。
    """
    t = preset["tokens"]
    primary = t.get("primary", "#173C8F")
    accent = t.get("accent", "#49B894")
    bg = t.get("bg", "#F4F0E7")
    return f"""
/* ---- ambient motion · 墨水落纸（htmlninefox） ---- */
.fox-ambient {{
  position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(42% 34% at 18% 12%, color-mix(in srgb, {primary} 16%, transparent), transparent 70%),
    radial-gradient(38% 30% at 84% 22%, color-mix(in srgb, {accent} 20%, transparent), transparent 72%),
    radial-gradient(30% 26% at 60% 88%, color-mix(in srgb, {primary} 10%, transparent), transparent 70%),
    {bg};
  background-size: 200% 200%, 190% 190%, 220% 220%, auto;
  animation: fox-ambient-drift 26s ease-in-out infinite alternate;
}}
@keyframes fox-ambient-drift {{
  0%   {{ background-position: 0% 0%, 100% 0%, 40% 100%, 0 0; }}
  100% {{ background-position: 34% 22%, 62% 30%, 76% 62%, 0 0; }}
}}
.fox-cursor-glow {{
  position: fixed; z-index: 0; pointer-events: none; opacity: 0;
  width: 340px; height: 340px; margin: -170px 0 0 -170px;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, {accent} 14%, transparent), transparent 78%);
  transition: opacity .5s ease;
}}
@media (pointer: fine) {{
  body.fox-glow-on .fox-cursor-glow {{ opacity: 1; }}
}}
.fox-ink-in > h1 {{
  animation: fox-ink-drop .7s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
@keyframes fox-ink-drop {{
  from {{ opacity: 0; transform: translateY(14px); filter: blur(6px); }}
  to   {{ opacity: 1; transform: none; filter: none; }}
}}
.fox-reveal {{
  opacity: 0; transform: translateY(18px);
  transition: opacity .6s cubic-bezier(0.16, 1, 0.3, 1),
              transform .6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: var(--fox-stagger, 0ms);
}}
.fox-reveal.fox-in {{ opacity: 1; transform: none; }}
.card {{ transition: transform .18s ease, box-shadow .18s ease; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 28px color-mix(in srgb, {primary} 12%, transparent); }}
:focus-visible {{ outline: 3px solid color-mix(in srgb, {accent} 70%, {primary}); outline-offset: 2px; border-radius: 2px; }}
:focus-visible {{ outline: 3px solid color-mix(in srgb, {accent} 70%, {primary}); outline-offset: 2px; border-radius: 2px; }}
@media (prefers-reduced-motion: reduce) {{
  .fox-ambient {{ animation: none; }}
  .fox-ink-in > h1 {{ animation: none; }}
  .fox-reveal {{ opacity: 1; transform: none; transition: none; }}
  .card {{ transition: none; }}
  .card:hover {{ transform: none; }}
  .fox-cursor-glow {{ display: none; }}
}}
@media print {{
  .fox-ambient {{ animation: none; }}
  .fox-reveal {{ opacity: 1 !important; transform: none !important; }}
  .fox-cursor-glow {{ display: none !important; }}
}}
"""


def ambient_motion_js() -> str:
    """动效层的最小 JS：自动标注 + 滚动显形 + 光标辉光。

    自动标注（渐进增强，渲染器零改动）：
      * 第一个 h1 的父容器加 .fox-ink-in（墨水落纸标题）；
      * `.card` 加 .fox-reveal（滚动进入视口时按次序 stagger）。
    reduced-motion 或无 IO 时所有元素直接以终态呈现。
    """
    return """<script>
(function(){
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var firstH1 = document.querySelector('h1');
  if (firstH1 && firstH1.parentElement) firstH1.parentElement.classList.add('fox-ink-in');
  var cards = document.querySelectorAll('.card');
  var targets = [];
  cards.forEach(function (el) {
    if (el.closest('nav')) return;
    el.classList.add('fox-reveal');
    targets.push(el);
  });
  if (reduce || !('IntersectionObserver' in window)) {
    targets.forEach(function (el) { el.classList.add('fox-in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        el.style.setProperty('--fox-stagger',
          Math.min(360, (parseInt(el.dataset.foxIndex || '0', 10)) * 60) + 'ms');
        el.classList.add('fox-in');
        io.unobserve(el);
      });
    }, { threshold: 0.12 });
    targets.forEach(function (el, i) {
      el.dataset.foxIndex = i % 7;
      io.observe(el);
    });
    /* 内容安全兜底：任何环境（无滚动事件的截图器、嵌入预览）下
       超过 1.8s 仍未显形的元素直接以终态呈现——内容永远不可见是
       比少一段编排更严重的失败。 */
    setTimeout(function () {
      targets.forEach(function (el) { el.classList.add('fox-in'); });
    }, 1800);
  }
  if (matchMedia('(pointer: fine)').matches && !reduce) {
    var glow = document.createElement('div');
    glow.className = 'fox-cursor-glow';
    document.body.appendChild(glow);
    document.body.classList.add('fox-glow-on');
    var raf = 0, x = 0, y = 0;
    addEventListener('pointermove', function (e) {
      x = e.clientX; y = e.clientY;
      if (!raf) raf = requestAnimationFrame(function () {
        glow.style.transform = 'translate(' + x + 'px,' + y + 'px)';
        raf = 0;
      });
    }, { passive: true });
  }
})();
</script>"""


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
<div class="fox-ambient" aria-hidden="true"></div>
{body}
{ambient_motion_js()}
</body>
</html>"""


def content_of(brief: dict, key: str, default: str = "") -> str:
    """从 brief（兼容嵌套/扁平）取 content 字段。"""
    payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
    c = payload.get("content", {}) or {}
    return str(c.get(key) or default)


def blocks_of(assets: dict) -> list:
    """The ids of the selected sections, whatever shape the blocks arrived in.

    Still "a list of ids" — all six renderers branch on membership, and that is
    not changing. What is new is that a block may carry content alongside its
    id, so a dict is reduced to its id here. Use `sections_of` when the content
    is what you want; using this for anything but membership would throw the
    content away.
    """
    if not isinstance(assets, dict):
        return []
    out = []
    for block in (assets.get("blocks") or []):
        if isinstance(block, str):
            out.append(block)
        elif isinstance(block, dict) and block.get("id"):
            out.append(str(block["id"]))
    return out


def sections_of(assets: dict) -> list:
    """The blocks that carry content of their own, as dicts.

    Parallel to `blocks_of` rather than a change to it: the six renderers depend
    on `blocks_of` meaning ids, and a page's sections must be able to arrive
    without that shifting underneath them. String blocks — which is everything
    every existing project has — simply produce an empty list here, and the
    renderer falls back to its own copy.
    """
    if not isinstance(assets, dict):
        return []
    return [b for b in (assets.get("blocks") or [])
            if isinstance(b, dict) and b.get("content")]


def page_sections_of(assets: dict) -> list:
    """The sections a page contributed, as dicts.

    Only `kind == "sections"` blocks count, and only those that actually carry
    prose — `sections_of` has already dropped the rest.

    A structure-only page returns [] and every renderer falls back to its
    built-in copy, which is the point: the licence decides, not the channel.

    Two bugs this one helper exists to prevent, both measured, not reasoned
    about:

    * A page's ids ("page-section-3", …) match none of a renderer's
      vocabulary, so `blocks_of` returning them skipped every branch and the
      project rendered blank — landing 0 body characters, archdoc 26.
    * `sections_of` drops a content-less section, but `blocks_of` still
      returned its id, which then displaced the default vocabulary. A
      structure-only page rendered blank for all six intents. That is every
      reference-licensed page, so this was the more common of the two.
    """
    return [s for s in sections_of(assets) if s.get("kind") == "sections"]


def block_ids_of(assets: dict, vocabulary: list) -> list:
    """Which vocabulary entries to render, given the blocks a project carries.

    Drops any id the renderer does not recognise. A block list made entirely of
    page ids used to shadow the vocabulary and blank the page; falling back to
    the built-in copy when nothing matches is both the old behaviour for empty
    projects and the correct outcome for a structure-only page.

    `blocks_of` keeps its meaning — the ids present — because six renderers
    branch on membership and that contract must not shift underneath them.
    This is the decision built on top of it.
    """
    present = blocks_of(assets)
    return [v for v in vocabulary if v in present] or vocabulary


def page_sections_html(
    sections: list,
    *,
    section_cls: str,
    item_cls: str = "card",
    heading_tag: str = "h2",
) -> str:
    """Render a page's sections using a renderer's own existing CSS classes.

    Each renderer passes the classes it already styles, so the page's prose
    lands in the look the project already has rather than in a second,
    unstyled markup dialect that would have to be styled six more times.
    """
    return "".join(
        f'<section class="{section_cls}"><{heading_tag}>{esc(s.get("heading") or "")}</{heading_tag}>'
        f'<div class="{item_cls}"><p>{esc(s.get("content") or "")}</p></div></section>'
        for s in sections)


def brand_of(brief: dict) -> str:
    """An explicitly empty brand means "no brand" — only a missing one is a demo.

    Word 导入没有品牌字段；以前显式传 "" 也会被兜底成 "Your Product"，于是一份
    客户的方案页顶着占位符发出去。缺字段仍给占位（演示与测试依赖它），给了空
    字符串就当真随空走。
    """
    payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
    content = payload.get("content", {}) or {}
    if "brand" in content or "brand" in payload:
        return str(content.get("brand") or payload.get("brand") or "")
    return "Your Product"


def brand_line(brand: str, suffix: str) -> str:
    """`brand · suffix`，没有品牌时就只印 suffix——不印"· 标题"这种断头。"""
    return f"{brand} · {suffix}" if brand else suffix
