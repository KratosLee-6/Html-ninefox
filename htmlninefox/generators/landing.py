"""landing.py · 落地页生成器（SaaS/产品官网）

区块：nav → hero → features → showcase → pricing → faq → cta_footer
数据源：brief.content（brand/core_message/must_have）+ assets 规划。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
.nav { display:flex; align-items:center; justify-content:space-between; padding:20px 0; }
.nav .logo { font-weight:800; font-size:1.15rem; color:var(--fox-text); }
.nav nav a { margin-left:28px; color:var(--fox-muted); font-size:.95rem; }
.nav nav a:hover { color:var(--fox-text); }
.hero { text-align:center; padding:96px 0 72px; }
.hero h1 { font-size: clamp(2.2rem, 5vw, 3.6rem); letter-spacing:-.02em; margin:20px 0 18px; }
.hero p.lead { font-size:1.2rem; color:var(--fox-muted); max-width:640px; margin:0 auto 32px; }
.hero .actions { display:flex; gap:14px; justify-content:center; }
.hero .panel { margin-top:56px; padding:12px; border-radius: calc(var(--fox-radius) + 6px);
  background:linear-gradient(180deg, var(--fox-border), transparent 60%); }
.hero .panel-inner { border-radius: var(--fox-radius); background:var(--fox-surface);
  border:1px solid var(--fox-border); padding:56px 24px; color:var(--fox-muted);
  font-family:var(--fox-font_body); font-size:.95rem; }
section.block { padding: var(--fox-space) 0; }
.sec-head { max-width:620px; margin-bottom:44px; }
.sec-head .kicker { color:var(--fox-primary); font-weight:700; font-size:.85rem;
  text-transform:uppercase; letter-spacing:.12em; }
.sec-head h2 { font-size:2rem; margin:10px 0 12px; letter-spacing:-.01em; }
.grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }
.grid2 { display:grid; grid-template-columns:repeat(2,1fr); gap:20px; }
.feature { padding:28px; }
.feature .ico { width:40px; height:40px; border-radius:10px; display:flex; align-items:center;
  justify-content:center; background:color-mix(in srgb, var(--fox-primary) 12%, transparent);
  color:var(--fox-primary); font-weight:800; margin-bottom:16px; }
.feature h3 { font-size:1.08rem; margin-bottom:8px; }
.feature p { color:var(--fox-muted); font-size:.95rem; }
.showcase { display:grid; grid-template-columns:1.2fr 1fr; gap:48px; align-items:center; }
.showcase .mock { padding:40px 28px; font-family:'JetBrains Mono',monospace; font-size:.85rem;
  color:var(--fox-muted); line-height:2; }
.showcase .mock b { color:var(--fox-accent); }
.showcase h2 { font-size:1.7rem; margin-bottom:14px; }
.showcase ul { list-style:none; margin-top:16px; }
.showcase li { padding:6px 0 6px 26px; position:relative; color:var(--fox-muted); }
.showcase li::before { content:'✓'; position:absolute; left:0; color:var(--fox-accent); font-weight:800; }
.pricing { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }
.plan { padding:30px; position:relative; }
.plan.hot { border-color:var(--fox-primary); box-shadow:0 0 0 1px var(--fox-primary); }
.plan .price { font-size:2.2rem; font-weight:800; margin:12px 0 4px; }
.plan .per { color:var(--fox-muted); font-size:.85rem; }
.plan ul { list-style:none; margin:18px 0 24px; }
.plan li { padding:5px 0 5px 24px; position:relative; font-size:.93rem; color:var(--fox-muted); }
.plan li::before { content:'✓'; position:absolute; left:0; color:var(--fox-primary); }
.plan .hot-badge { position:absolute; top:-12px; right:20px; background:var(--fox-primary);
  color:var(--fox-primary_text); font-size:.75rem; padding:3px 12px; border-radius:999px; }
.faq details { border:1px solid var(--fox-border); border-radius:var(--fox-radius);
  background:var(--fox-surface); padding:18px 22px; margin-bottom:12px; }
.faq summary { cursor:pointer; font-weight:600; }
.faq details p { margin-top:10px; color:var(--fox-muted); font-size:.95rem; }
.cta { text-align:center; padding: calc(var(--fox-space) * 1.2) 0; }
.cta h2 { font-size:2.1rem; margin-bottom:14px; }
.cta p { color:var(--fox-muted); margin-bottom:28px; }
footer { border-top:1px solid var(--fox-border); padding:32px 0; color:var(--fox-muted);
  font-size:.88rem; display:flex; justify-content:space-between; }
@media (max-width: 860px) {
  .grid3, .pricing { grid-template-columns:1fr; }
  .grid2, .showcase { grid-template-columns:1fr; }
}
"""


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    core = content_of(brief, "core_message", "为高效团队打造的下一代工作台")
    headline = content_of(brief, "headline", core)
    must_have = (brief.get("brief", brief).get("content", {}) or {}).get("must_have", []) \
        if isinstance(brief, dict) else []

    feats = (must_have + ["一键上手，5 分钟完成配置", "私有化部署，数据不出内网", "开放 API，接入现有流程"])[:6]
    f_blocks = [f"""
      <div class="feature card">
        <div class="ico">0{i + 1}</div>
        <h3>{esc(f)}</h3>
        <p>围绕「{esc(f)}」设计的完整能力，与工作流无缝衔接。</p>
      </div>""" for i, f in enumerate(feats[:3])]
    f_blocks2 = [f"""
      <div class="feature card">
        <div class="ico">0{i + 4}</div>
        <h3>{esc(f)}</h3>
        <p>稳定可靠，开箱即用。</p>
      </div>""" for i, f in enumerate(feats[3:6])]

    plans = [
        ("免费版", "¥0", "/月", ["核心功能全量", "单人使用", "社区支持"], False),
        ("专业版", "¥99", "/月", ["全部核心功能", "多人协作（10 席）", "优先客服", "自定义品牌"], True),
        ("企业版", "联系我们", "", ["私有化部署", "SSO / 审计日志", "专属客户成功"], False),
    ]
    plan_html = "".join(f"""
      <div class="plan card{' hot' if hot else ''}">
        {'<span class="hot-badge">最受欢迎</span>' if hot else ''}
        <h3>{esc(name)}</h3>
        <div class="price">{esc(price)}</div><div class="per">{esc(per)}</div>
        <ul>{''.join(f'<li>{esc(item)}</li>' for item in items)}</ul>
        <a class="btn{' ghost' if not hot else ''}" href="#">{esc('开始使用' if hot else '选择方案')}</a>
      </div>""" for name, price, per, items, hot in plans)

    faqs = [
        ("数据安全如何保障？", "传输全程 TLS 加密，支持私有化部署，数据完全留在你的环境内。"),
        ("可以随时取消订阅吗？", "可以。按月订阅随时取消，取消后服务持续到当前计费周期结束。"),
        ("是否提供 API？", "提供。全部能力均开放 REST API 与 Webhook，文档随产品一同更新。"),
    ]
    faq_html = "".join(f"""
      <details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>""" for q, a in faqs)

    blocks = blocks_of(assets) or ["nav", "hero", "features", "showcase", "pricing", "faq", "cta_footer"]

    parts = []
    if "nav" in blocks:
        parts.append(f"""
<header class="wrap nav">
  <div class="logo">🦊 {esc(brand)}</div>
  <nav><a href="#features">功能</a><a href="#pricing">定价</a><a href="#faq">常见问题</a></nav>
  <a class="btn" href="#cta">免费开始</a>
</header>""")

    if "hero" in blocks:
        parts.append(f"""
<section class="wrap hero">
  <span class="tag">{esc(brand)} · 正式发布</span>
  <h1>{esc(headline)}</h1>
  <p class="lead">{esc(content_of(brief, "hero_sub", "把想法变成可交付的成果，只差一个开始。"))}</p>
  <div class="actions"><a class="btn" href="#cta">免费开始</a><a class="btn ghost" href="#features">了解功能 →</a></div>
  <div class="panel"><div class="panel-inner">▣ {esc(brand)} 产品界面预览区<br>—— 由 Html九尾狐 生成 · {esc(preset['name'])} 风格 ——</div></div>
</section>""")

    if "features" in blocks:
        parts.append(f"""
<section class="wrap block" id="features">
  <div class="sec-head"><span class="kicker">FEATURES</span>
    <h2>为真实工作流而生</h2>
    <p class="muted">不是又一个工具，而是把你的经验沉淀成可复用的资产。</p></div>
  <div class="grid3">{''.join(f_blocks)}</div>
  <div class="grid3" style="margin-top:20px">{''.join(f_blocks2)}</div>
</section>""")

    if "showcase" in blocks:
        parts.append(f"""
<section class="wrap block">
  <div class="showcase">
    <div class="mock card">▸ connect({esc(brand.lower())})<br>▸ sync&nbsp;&nbsp;··· done <b>✓</b><br>▸ build&nbsp;··· done <b>✓</b><br>▸ ship&nbsp;&nbsp;··· live <b>🚀</b></div>
    <div>
      <span class="tag">WORKFLOW</span>
      <h2 style="margin-top:14px">三步接入，即刻提效</h2>
      <ul><li>连接现有工具链，无需迁移</li><li>配置一次，团队共享</li><li>持续沉淀，越用越懂你</li></ul>
      <a class="btn" style="margin-top:18px" href="#cta">立即体验</a>
    </div>
  </div>
</section>""")

    if "pricing" in blocks:
        parts.append(f"""
<section class="wrap block" id="pricing">
  <div class="sec-head"><span class="kicker">PRICING</span>
    <h2>简单透明的定价</h2><p class="muted">按需选择，随时升级或取消。</p></div>
  <div class="pricing">{plan_html}</div>
</section>""")

    if "faq" in blocks:
        parts.append(f"""
<section class="wrap block faq" id="faq">
  <div class="sec-head"><span class="kicker">FAQ</span><h2>常见问题</h2></div>
  {faq_html}
</section>""")

    if "cta_footer" in blocks:
        parts.append(f"""
<section class="wrap block cta" id="cta">
  <h2>现在开始，让下一次交付更快</h2>
  <p>免费注册，无需信用卡。</p>
  <a class="btn" href="#">免费开始 →</a>
</section>
<footer class="wrap"><span>© 2026 {esc(brand)}</span><span>Powered by Html九尾狐 · {esc(preset['name'])}</span></footer>""")

    return html_shell(f"{brand} · {content_of(brief, 'core_message', '产品官网')[:40]}",
                      preset, "\n".join(parts), _EXTRA, generator=f"htmlninefox-v0.2/landing")
