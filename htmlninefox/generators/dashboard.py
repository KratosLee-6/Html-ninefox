"""dashboard.py · 数据看板生成器（管理后台/BI 概览）

区块：topbar → kpi_row → charts → table → activity
图表用纯 CSS 柱状/环形（无外部依赖），数据来自 assets['chart_data'] 或默认样例。
"""

from __future__ import annotations

from typing import Any, Dict

from ._shared import base_css, blocks_of, brand_of, content_of, esc, html_shell

_EXTRA = """
.shell { display:grid; grid-template-columns:220px 1fr; min-height:100vh; }
.side { background:var(--fox-surface); border-right:1px solid var(--fox-border); padding:20px 14px; }
.side .logo { font-weight:800; margin-bottom:26px; padding:0 10px; }
.side a { display:block; padding:9px 12px; border-radius:8px; color:var(--fox-muted);
  font-size:.92rem; margin-bottom:2px; }
.side a.on, .side a:hover { background:color-mix(in srgb, var(--fox-primary) 12%, transparent);
  color:var(--fox-primary); font-weight:600; }
.main { padding:0 28px 40px; }
.topbar { display:flex; align-items:center; justify-content:space-between;
  padding:18px 0 22px; }
.topbar h1 { font-size:1.3rem; }
.topbar .who { display:flex; align-items:center; gap:10px; color:var(--fox-muted); font-size:.88rem; }
.topbar .ava { width:30px; height:30px; border-radius:50%; background:var(--fox-primary);
  color:var(--fox-primary_text); display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:.8rem; }
.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.kpi { padding:20px; }
.kpi .label { color:var(--fox-muted); font-size:.85rem; }
.kpi .val { font-size:1.9rem; font-weight:800; margin:6px 0 4px; letter-spacing:-.01em; }
.kpi .delta { font-size:.82rem; font-weight:600; }
.up { color:#22C55E; } .down { color:#EF4444; }
.charts { display:grid; grid-template-columns:2fr 1fr; gap:16px; margin-top:16px; }
.chart { padding:22px; }
.chart h3 { font-size:1rem; margin-bottom:18px; }
.bars { display:flex; align-items:flex-end; gap:10px; height:180px; }
.bar { flex:1; border-radius:6px 6px 2px 2px; background:color-mix(in srgb,
  var(--fox-primary) 32%, transparent); position:relative; }
.bar.hot { background:var(--fox-primary); }
.bar span { position:absolute; bottom:-24px; left:0; right:0; text-align:center;
  font-size:.72rem; color:var(--fox-muted); }
.bars { margin-bottom:26px; }
.donut-wrap { display:flex; align-items:center; gap:22px; }
.donut { width:130px; height:130px; border-radius:50%;
  background:conic-gradient(var(--fox-primary) 0 62%, var(--fox-accent) 62% 84%,
    var(--fox-border) 84% 100%); position:relative; flex:none; }
.donut::after { content:'62%'; position:absolute; inset:22px; border-radius:50%;
  background:var(--fox-surface); display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:1.25rem; }
.legend { font-size:.85rem; color:var(--fox-muted); line-height:2.1; }
.dot { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:8px; }
.tbl { margin-top:16px; padding:6px 0 2px; overflow:auto; }
.tbl h3 { font-size:1rem; padding:16px 22px 8px; }
table { width:100%; border-collapse:collapse; font-size:.9rem; }
th { text-align:left; color:var(--fox-muted); font-weight:600; font-size:.8rem;
  padding:10px 22px; border-bottom:1px solid var(--fox-border); }
td { padding:12px 22px; border-bottom:1px solid var(--fox-border); }
tr:last-child td { border-bottom:none; }
.pill { padding:3px 10px; border-radius:999px; font-size:.78rem; font-weight:600; }
.pill.ok { background:color-mix(in srgb, #22C55E 16%, transparent); color:#22C55E; }
.pill.warn { background:color-mix(in srgb, var(--fox-accent) 16%, transparent);
  color:var(--fox-accent); }
.pill.err { background:color-mix(in srgb, #EF4444 16%, transparent); color:#EF4444; }
.activity { margin-top:16px; padding:22px; }
.activity h3 { font-size:1rem; margin-bottom:14px; }
.act { display:flex; gap:12px; padding:9px 0; font-size:.9rem; }
.act .t { color:var(--fox-muted); font-size:.8rem; flex:none; width:52px; }
@media (max-width: 960px) {
  .shell { grid-template-columns:1fr; } .side { display:none; }
  .kpis { grid-template-columns:repeat(2,1fr); } .charts { grid-template-columns:1fr; }
}
"""

_KPIS = [
    ("总用户数", "24,813", "+12.4%", "up"),
    ("月活跃", "8,392", "+5.1%", "up"),
    ("付费转化", "4.6%", "-0.8%", "down"),
    ("今日收入", "¥18,204", "+9.3%", "up"),
]

_ROWS = [
    ("#1024", "深圳·极狐科技", "专业版", "¥2,970", "ok", "已支付"),
    ("#1023", "上海·临港设计", "企业版", "¥12,800", "warn", "待审核"),
    ("#1022", "北京·白泽数据", "专业版", "¥5,940", "ok", "已支付"),
    ("#1021", "杭州·拾光传媒", "免费版", "¥0", "err", "已退款"),
    ("#1020", "成都·山止策划", "专业版", "¥2,970", "ok", "已支付"),
]

_ACTS = [
    ("09:41", "新订单", "白泽数据 升级为专业版"),
    ("09:12", "告警", "支付网关延迟 P99 > 800ms"),
    ("08:47", "新用户", "今日新增注册 47 人"),
    ("08:02", "部署", "v0.2.1 已发布至生产环境"),
]


def render(brief: dict, style: dict, assets: dict) -> str:
    preset = style
    brand = brand_of(brief)
    blocks = blocks_of(assets) or ["topbar", "kpi_row", "charts", "table", "activity"]

    parts = ['<div class="shell">',
             '<aside class="side"><div class="logo">▦ ' + esc(brand) + '</div>']
    for label, on in [("概览", True), ("订单", False), ("用户", False), ("报表", False),
                      ("告警", False), ("设置", False)]:
        parts.append(f'<a class="{"on" if on else ""}" href="#">{esc(label)}</a>')
    parts.append("</aside>")
    parts.append('<main class="main">')

    if "topbar" in blocks:
        parts.append(f"""
<header class="topbar"><h1>数据概览</h1>
  <div class="who"><span>2026-08-29 · 实时</span><div class="ava">KX</div></div>
</header>""")

    if "kpi_row" in blocks:
        parts.append('<section class="kpis">' + "".join(f"""
  <div class="kpi card"><div class="label">{esc(l)}</div>
    <div class="val">{esc(v)}</div><div class="delta {d}">{esc(delta)} vs 上周</div>
  </div>""" for l, v, delta, d in _KPIS) + "</section>")

    if "charts" in blocks:
        bars = [42, 58, 47, 71, 66, 88, 79]
        labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        bar_html = "".join(
            f'<div class="bar{" hot" if v == max(bars) else ""}" style="height:{v}%">'
            f'<span>{esc(labels[i])}</span></div>' for i, v in enumerate(bars))
        parts.append(f"""
<section class="charts">
  <div class="chart card"><h3>本周访问趋势</h3><div class="bars">{bar_html}</div></div>
  <div class="chart card"><h3>流量构成</h3>
    <div class="donut-wrap"><div class="donut"></div>
      <div class="legend">
        <div><span class="dot" style="background:var(--fox-primary)"></span>自然流量 62%</div>
        <div><span class="dot" style="background:var(--fox-accent)"></span>推荐渠道 22%</div>
        <div><span class="dot" style="background:var(--fox-border)"></span>直接访问 16%</div>
      </div></div>
  </div>
</section>""")

    if "table" in blocks:
        rows = "".join(f"""
  <tr><td>{esc(oid)}</td><td>{esc(name)}</td><td>{esc(plan)}</td><td>{esc(amt)}</td>
      <td><span class="pill {cls}">{esc(status)}</span></td></tr>"""
                       for oid, name, plan, amt, cls, status in _ROWS)
        parts.append(f"""
<section class="tbl card"><h3>最近订单</h3>
<table><thead><tr><th>单号</th><th>客户</th><th>套餐</th><th>金额</th><th>状态</th></tr></thead>
<tbody>{rows}</tbody></table></section>""")

    if "activity" in blocks:
        acts = "".join(f'<div class="act"><span class="t">{esc(t)}</span>'
                       f'<span><b>{esc(kind)}</b> · {esc(msg)}</span></div>'
                       for t, kind, msg in _ACTS)
        parts.append(f'<section class="activity card"><h3>动态</h3>{acts}</section>')

    parts.append("</main></div>")
    return html_shell(f"{brand} · 数据概览", preset, "\n".join(parts), _EXTRA,
                      generator="htmlninefox-v0.2/dashboard")
