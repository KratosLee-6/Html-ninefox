"""deck.py · 发布会 PPT 生成器（横向翻页 · guizang 电子杂志风致敬）

区块：cover → problem → solution → demo → metrics → roadmap → ending
交互：← → 方向键 / 点击箭头 / 底部圆点 翻页；纯原生 JS 零依赖。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
html, body { height:100%; overflow:hidden; }
.deck { height:100vh; display:flex; flex-direction:column; }
.slides { flex:1; position:relative; }
.slide { position:absolute; inset:0; display:flex; flex-direction:column;
  justify-content:center; padding:64px clamp(40px,8vw,120px); opacity:0;
  transform:translateX(40px); transition:opacity .45s ease, transform .45s ease;
  pointer-events:none; }
.slide.on { opacity:1; transform:none; pointer-events:auto; }
.slide .no { font-size:.85rem; color:var(--fox-primary); font-weight:800;
  letter-spacing:.2em; margin-bottom:18px; }
.slide h1 { font-size:clamp(2.4rem,6vw,4.6rem); letter-spacing:-.02em; line-height:1.15; }
.slide h2 { font-size:clamp(1.7rem,3.6vw,2.7rem); margin-bottom:22px; letter-spacing:-.01em; }
.slide p.sub { font-size:1.15rem; color:var(--fox-muted); margin-top:22px; max-width:640px; }
.cols { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-top:36px; }
.col { padding:26px; }
.col h4 { margin-bottom:10px; font-size:1.05rem; }
.col p { color:var(--fox-muted); font-size:.93rem; }
.big-num { font-size:clamp(3rem,8vw,5.4rem); font-weight:800; letter-spacing:-.03em;
  color:var(--fox-primary); }
.metric-row { display:grid; grid-template-columns:repeat(3,1fr); gap:24px; margin-top:30px; }
.metric p { color:var(--fox-muted); margin-top:6px; }
.rule { width:64px; height:4px; background:var(--fox-primary); border-radius:2px; margin-bottom:28px; }
.quote { font-size:clamp(1.2rem,2.6vw,1.7rem); line-height:1.8; max-width:820px; }
.quote em { color:var(--fox-primary); font-style:normal; font-weight:700; }
.demo-mock { margin-top:32px; padding:44px 32px; color:var(--fox-muted);
  font-family:'JetBrains Mono',monospace; font-size:.9rem; line-height:2.1; }
.demo-mock b { color:var(--fox-accent); }
.road { margin-top:30px; display:grid; gap:14px; max-width:760px; }
.road .step { display:flex; gap:16px; align-items:baseline; }
.road .q { font-weight:800; color:var(--fox-primary); flex:none; width:52px; }
.road .when { color:var(--fox-muted); font-size:.88rem; margin-left:auto; flex:none; }
.hud { display:flex; align-items:center; justify-content:space-between;
  padding:18px clamp(40px,8vw,120px); border-top:1px solid var(--fox-border); }
.hud .dots { display:flex; gap:8px; }
.hud .dot { width:8px; height:8px; border-radius:50%; background:var(--fox-border);
  cursor:pointer; transition:all .25s; }
.hud .dot.on { background:var(--fox-primary); transform:scale(1.3); }
.hud button { background:none; border:1px solid var(--fox-border); color:var(--fox-text);
  width:38px; height:38px; border-radius:50%; cursor:pointer; font-size:1rem; }
.hud button:hover { border-color:var(--fox-primary); color:var(--fox-primary); }
.hud .pg { font-size:.85rem; color:var(--fox-muted); font-variant-numeric:tabular-nums; }
.cover-tag { display:inline-block; border:1px solid var(--fox-border); border-radius:999px;
  padding:6px 18px; font-size:.85rem; color:var(--fox-muted); margin-bottom:26px; }
"""


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    core = content_of(brief, "core_message", "重新定义团队的创作方式")
    blocks = blocks_of(assets) or ["cover", "problem", "solution", "demo", "metrics", "roadmap", "ending"]

    def slide(no: str, inner: str) -> str:
        return f'<section class="slide">{inner}</section>'

    slides = []
    if "cover" in blocks:
        slides.append(slide("01", f"""
  <div class="cover-tag">{esc(brand)} · 发布会 2026</div>
  <h1>{esc(content_of(brief, "headline", core))}</h1>
  <p class="sub">—— {esc(brand)} · 由 Html九尾狐 编排生成 ——</p>"""))
    if "problem" in blocks:
        slides.append(slide("02", f"""
  <div class="rule"></div><h2>今天的问题</h2>
  <p class="quote">每一次创作都从零开始，<em>经验无法沉淀</em>，每一次交付都在重复昨天的劳动。</p>"""))
    if "solution" in blocks:
        cols = "".join(f"""
    <div class="col card"><h4>{esc(t)}</h4><p>{esc(d)}</p></div>""" for t, d in [
            ("Brief 标准", "五个字段说清目标，AI 不再猜你想要什么"),
            ("审美模板", "设计 token 沉淀复用，风格一次到位"),
            ("反馈迭代", "一轮轮具体反馈，改 token 而非重写")])
        slides.append(slide("03", f"""
  <div class="rule"></div><h2>{esc(brand)} 的解法</h2>
  <div class="cols">{cols}</div>"""))
    if "demo" in blocks:
        slides.append(slide("04", f"""
  <div class="rule"></div><h2>看它如何工作</h2>
  <div class="demo-mock card">$ htmlninefox expert "做一个发布会 keynote"<br>
    <b>brief_expert</b>&nbsp; ✓ 解析 Brief（confidence 0.82）<br>
    <b>style_expert</b>&nbsp; ✓ 匹配 {esc(preset['name'])}<br>
    <b>generate</b>&nbsp;&nbsp;&nbsp; ✓ 7 页横向翻页 · 零依赖<br>
    <b>feedback</b>&nbsp;&nbsp;&nbsp; ✓ 沉淀至反馈库</div>"""))
    if "metrics" in blocks:
        metrics = "".join(f"""
    <div class="metric"><div class="big-num">{esc(v)}</div><p>{esc(l)}</p></div>"""
                          for v, l in [("5 类", "内容类型开箱即用"), ("3 端", "CLI / Web / Skill"),
                                       ("0 元", "MIT 开源 · 离线可用")])
        slides.append(slide("05", f'<div class="rule"></div><h2>数字说话</h2>'
                                f'<div class="metric-row">{metrics}</div>'))
    if "roadmap" in blocks:
        steps = "".join(f"""
    <div class="step"><span class="q">0{i + 1}</span><span>{esc(t)}</span>
      <span class="when">{esc(w)}</span></div>"""
                        for i, (t, w) in enumerate([
                            ("个人版 CLI 正式开源", "2026 Q3"),
                            ("Skill 联盟 · 3 个头部 skill 接入", "2026 Q4"),
                            ("模板市场 30 SKU", "2027 Q1"),
                            ("企业级能力（社区驱动）", "按需")]))
        slides.append(slide("06", f'<div class="rule"></div><h2>路线图</h2><div class="road">{steps}</div>'))
    if "ending" in blocks:
        slides.append(slide("07", f"""
  <h1>谢谢观看</h1>
  <p class="sub">Html九尾狐 · 让设计师/前端用「Brief + 审美模板 + 一轮轮反馈」做出能交付的 HTML</p>
  <p class="sub"><b>{esc(brand)}</b> · MIT Open Source</p>"""))

    n = len(slides)
    dots = "".join(f'<span class="dot{" on" if i == 0 else ""}" data-i="{i}"></span>'
                   for i in range(n))
    body = f"""
<div class="deck">
  <div class="slides">{''.join(slides)}</div>
  <div class="hud">
    <span class="pg"><b id="cur">1</b> / {n}</span>
    <div class="dots">{dots}</div>
    <div><button id="prev" aria-label="上一页">←</button>
         <button id="next" aria-label="下一页">→</button></div>
  </div>
</div>
<script>
(function() {{
  var slides = document.querySelectorAll('.slide');
  var dots = document.querySelectorAll('.hud .dot');
  var cur = document.getElementById('cur');
  var idx = 0;
  function go(i) {{
    idx = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach(function(s, j) {{ s.classList.toggle('on', j === idx); }});
    dots.forEach(function(d, j) {{ d.classList.toggle('on', j === idx); }});
    cur.textContent = idx + 1;
  }}
  document.getElementById('next').onclick = function() {{ go(idx + 1); }};
  document.getElementById('prev').onclick = function() {{ go(idx - 1); }};
  dots.forEach(function(d) {{ d.onclick = function() {{ go(+d.dataset.i); }}; }});
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') go(idx + 1);
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') go(idx - 1);
  }});
  go(0);
}})();
</script>"""

    return html_shell(f"{brand} · 发布会", preset, body, _EXTRA, generator="htmlninefox-v0.2/deck")
