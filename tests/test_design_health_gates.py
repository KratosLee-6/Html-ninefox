"""v0.6 设计体检修复的回归门禁。

这些断言锁住 2026-09-29 设计体检发现并修复的界面缺陷。每一条都对应一次
真实缺陷，而不是对当前实现的复述——去掉任一修复，本文件必须变红。

覆盖：
  1. intakeFetchBatch 曾经未定义，「批量抓取」按钮一点就 ReferenceError。
  2. 节点头部标题折行会把类型徽标压成竖排单字。
  3. 窄屏曾把五个步骤名全部隐藏，进度条只剩无含义的圆点。
  4. 弱化文字对比度曾低于 WCAG AA（纸白 3.17–3.51:1）。
  5. 夜蓝主题的 accent 底曾配死白字，主按钮只有 2.44:1。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"
INDEX = STATIC / "index.html"

READY = "window.FoxWorkbenchUI && window.FoxIntake && nodes.length >= 1"


def _rel_luminance(rgb: tuple[float, float, float]) -> float:
    channels = []
    for value in rgb:
        value /= 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _parse(color: str) -> tuple[tuple[float, float, float], float]:
    match = re.match(r"rgba?\(([^)]+)\)", color)
    assert match, f"无法解析颜色：{color!r}"
    parts = [float(value) for value in match.group(1).split(",")]
    return tuple(parts[:3]), (parts[3] if len(parts) > 3 else 1.0)


CONTRAST_PROBE = """
() => {
  const parse = s => { const m = s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(',').map(parseFloat); return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }; };
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (f, b) => { const hi = Math.max(lum(f), lum(b)), lo = Math.min(lum(f), lum(b));
    return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100; };
  const effBg = el => {
    const own = parse(getComputedStyle(el).backgroundColor);
    if (own && own.a > 0.5) return own.rgb;          // 半透明徽标用自己的底色
    let n = el.parentElement;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.85) return c.rgb;
      n = n.parentElement;
    }
    return [255, 255, 255];
  };
  const fails = [];
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    if (el.closest('.tl-dot')) return;               // 图形符号，适用 3:1 非文本标准
    const text = [...el.childNodes].filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim()).join(' ').trim();
    if (!text || el.children.length) return;
    const fg = parse(cs.color);
    if (!fg) return;
    const size = Math.round(parseFloat(cs.fontSize) * 10) / 10;
    const large = size >= 24 || (size >= 18.66 && Number(cs.fontWeight) >= 700);
    const need = large ? 3 : 4.5;
    const got = ratio(fg.rgb, effBg(el));
    if (got < need) fails.push({ size, got, need, sel: String(el.className || el.tagName), text: text.slice(0, 20) });
  });
  return fails;
}
"""


@pytest.fixture
def audited_page(workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/")
        page.wait_for_function(READY, timeout=20000)
        page.wait_for_timeout(600)
        yield page, errors
        browser.close()


def test_batch_fetch_button_is_wired(audited_page) -> None:
    """「批量抓取」曾经是死按钮：onclick 调用的全局函数从未定义。"""
    page, errors = audited_page
    assert page.evaluate("typeof window.intakeFetchBatch") == "function", (
        "intakeFetchBatch 未定义，审核台的「批量抓取」按钮会抛 ReferenceError")
    assert page.locator("#intake-batch-btn").count() == 1
    assert not errors


def test_node_head_badge_is_not_squeezed_vertical(audited_page) -> None:
    """长中文标题曾把 .kind 徽标压成 12x21 的竖排单字。

    判定用「宽 > 高」而不是固定尺寸：两字徽标单行时约 19x14（宽大于高），
    被挤成上下两行时约 12x21（宽小于高）。比值对字号变化不敏感。
    """
    page, _ = audited_page
    heads = page.evaluate("""
    () => [...document.querySelectorAll('.node-head')].map(h => {
      const k = h.querySelector('.kind');
      if (!k) return null;
      const r = k.getBoundingClientRect();
      return { text: k.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height),
               lines: Math.round(k.scrollHeight / Math.max(1, parseFloat(getComputedStyle(k).lineHeight) || 1)) };
    }).filter(Boolean)
    """)
    assert heads, "画布上应至少有一个带类型徽标的节点"
    for kind in heads:
        assert kind["w"] > kind["h"], (
            f"徽标「{kind['text']}」被挤成竖排：{kind['w']}x{kind['h']}，"
            f"标题应先截断而不是挤压徽标")


def test_narrow_viewport_keeps_current_step_label(audited_page) -> None:
    """窄屏曾隐藏全部步骤名，只剩无含义的圆点。"""
    page, _ = audited_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(600)
    labels = page.evaluate("""
    () => [...document.querySelectorAll('.tl-stage')].map(s => {
      const l = s.querySelector('.tl-label');
      const shown = l && getComputedStyle(l).display !== 'none' && s.offsetParent !== null;
      return { text: (l || {}).textContent || '', shown: !!shown,
               active: s.classList.contains('active') || s.classList.contains('failed') };
    })
    """)
    assert labels
    active_shown = [item for item in labels if item["active"]]
    assert active_shown, "时间线应至少有一个当前或失败步骤"
    for item in active_shown:
        assert item["shown"], f"当前步骤「{item['text']}」在窄屏不可见，进度信息等于不存在"


@pytest.mark.parametrize("theme", ["pixel-paper", "pixel-night"])
def test_deemphasised_text_meets_wcag_aa(audited_page, theme: str) -> None:
    """弱化文字曾用同一个灰蓝色：纸白 3.17–3.51:1，夜蓝 3.98:1，均低于 AA。"""
    page, _ = audited_page
    page.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
    page.wait_for_timeout(400)
    fails = page.evaluate(CONTRAST_PROBE)
    assert not fails, "以下文字低于 WCAG AA：" + "; ".join(
        f"{item['got']}:1 (需 {item['need']}) {item['size']}px {item['sel']} 「{item['text']}」"
        for item in fails[:8])


def test_accent_surface_uses_theme_aware_foreground(audited_page) -> None:
    """夜蓝 accent 是亮蓝，配死白字会让主按钮只有 2.44:1。"""
    page, _ = audited_page
    for theme in ("pixel-paper", "pixel-night"):
        page.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
        page.wait_for_timeout(300)
        pair = page.evaluate("""
        () => { const cs = getComputedStyle(document.querySelector('#btn-go'));
          return { bg: cs.backgroundColor, fg: cs.color }; }
        """)
        bg, bg_alpha = _parse(pair["bg"])
        fg, fg_alpha = _parse(pair["fg"])
        assert bg_alpha > 0.5 and fg_alpha > 0.5, pair
        hi, lo = sorted((_rel_luminance(bg), _rel_luminance(fg)), reverse=True)
        ratio = (hi + 0.05) / (lo + 0.05)
        assert ratio >= 4.5, f"{theme} 主按钮对比度仅 {ratio:.2f}:1（{pair}）"
