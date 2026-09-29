"""工作台设计体检：可复现的界面度量扫描。

用途
----
把「界面好不好看、够不够用」变成可回归的数字。2026-09-29 的设计体检
（docs/AUDIT-DESIGN-20260929.md）就是用这套度量发现的真实缺陷。

用法
----
    python scripts/design_audit.py                       # 打印摘要
    python scripts/design_audit.py --out docs/audit-run  # 同时落 JSON 与截图
    python scripts/design_audit.py --base http://127.0.0.1:8620

先启动工作台（`htmlninefox app`）或指定 --base。

三条探针规则（都是第一版实测踩过的坑，改动前请先读）
------------------------------------------------------------
1. 半透明自身底色：`.template-badge` 是白字压在 rgba(17,28,42,.82) 上。
   若像普通元素那样向上穿透找不透明祖先，会得到「对比度 1:1」的假警报。
   规则：元素自身背景 alpha > 0.5 时就用自己的底色。
2. 画布缩放：`.node-head` / `.ws-head` 内的控件随 `camera.z` 缩放，
   在非 100% 缩放下量 getBoundingClientRect 测的是缩放而不是控件。
   规则：触控目标一律在 camera.z = 1 下量。
3. 主题值：夜蓝主题是 `data-theme="pixel-night"`，不是 `"night"`。
   写错不会报错，只会静默量到纸白的数据——第一版就是这么把两个主题
   的数值测成一样的。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - 缺依赖时给出可操作的提示
    sys.exit("需要 playwright：python -m pip install playwright && python -m playwright install chromium")

READY = "window.FoxWorkbenchUI && nodes.length >= 1"

# 图形符号（粗体 ✓ 等）适用 WCAG 非文本 3:1，不适用文字 4.5:1
NON_TEXT = ".tl-dot, .recipe-stage-dot"

PROBE = """
(opts) => {
  const parse = s => { const m = s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(',').map(parseFloat); return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }; };
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (f, b) => { const hi = Math.max(lum(f), lum(b)), lo = Math.min(lum(f), lum(b));
    return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100; };
  const effBg = el => {
    const own = parse(getComputedStyle(el).backgroundColor);
    if (own && own.a > 0.5) return own.rgb;              // 规则 1
    let n = el.parentElement;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.85) return c.rgb;
      n = n.parentElement;
    }
    return [255, 255, 255];
  };
  const isCanvas = el => !!(el.closest('#viewport') || el.closest('.canvas-wrap'));

  const contrast = [], small = [], type = new Map();
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || r.bottom < 0 || r.top > innerHeight * 4) return;

    const text = [...el.childNodes].filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim()).join(' ').trim();
    if (text) {
      const key = cs.fontSize + '|' + cs.lineHeight + '|' + cs.fontWeight;
      type.set(key, (type.get(key) || 0) + 1);
      if (!el.children.length && !el.closest(opts.nonText)) {
        const fg = parse(cs.color);
        if (fg) {
          const size = Math.round(parseFloat(cs.fontSize) * 10) / 10;
          const large = size >= 24 || (size >= 18.66 && Number(cs.fontWeight) >= 700);
          const need = large ? 3 : 4.5;
          const got = ratio(fg.rgb, effBg(el));
          if (got < need) contrast.push({ size, got, need,
            sel: String(el.className || el.tagName), text: text.slice(0, 24) });
        }
      }
    }
    if ((el.tagName === 'BUTTON' || el.tagName === 'A') && !el.closest('[hidden]')
        && !isCanvas(el) && (r.width < 24 || r.height < 24)) {
      small.push({ label: (el.getAttribute('aria-label') || el.title || el.textContent || '')
        .trim().slice(0, 18), w: Math.round(r.width), h: Math.round(r.height) });
    }
  });
  const badges = [...document.querySelectorAll('.node-head .kind')].map(k => {
    const r = k.getBoundingClientRect();
    return { text: k.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height) };
  });
  return { contrast, small, typeSizeCount: type.size, badges };
}
"""

VIEWPORTS = [("desktop-1440", 1440, 900), ("tablet-768", 768, 1024), ("mobile-390", 390, 844)]
THEMES = ["pixel-paper", "pixel-night"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Html九尾狐 工作台设计体检")
    parser.add_argument("--base", default="http://127.0.0.1:8620", help="工作台地址")
    parser.add_argument("--out", type=Path, help="落盘目录（写 audit.json 与截图）")
    args = parser.parse_args()

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(args.base + "/")
        try:
            page.wait_for_function(READY, timeout=20000)
        except Exception:
            print(f"无法在 {args.base} 打开工作台（{READY} 超时）")
            browser.close()
            return 2
        page.wait_for_timeout(600)

        for theme in THEMES:  # 规则 3
            page.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
            page.wait_for_timeout(400)
            report[f"contrast-{theme}"] = page.evaluate(PROBE, {"nonText": NON_TEXT})

        page.evaluate("document.documentElement.dataset.theme = 'pixel-paper'")
        page.wait_for_timeout(300)
        page.evaluate("camera.z=1; applyCamera(false,false)")  # 规则 2
        page.wait_for_timeout(600)
        report["desktop-1440"] = page.evaluate(PROBE, {"nonText": NON_TEXT})
        if args.out:
            page.screenshot(path=str(args.out / "desktop-1440.png"))

        for name, width, height in VIEWPORTS[1:]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(700)
            report[name] = page.evaluate(PROBE, {"nonText": NON_TEXT})
            if args.out:
                page.screenshot(path=str(args.out / f"{name}.png"))

        report["_pageErrors"] = errors
        browser.close()

    if args.out:
        (args.out / "audit.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写出 {args.out / 'audit.json'}")

    print("\n设计体检摘要")
    print("=" * 46)
    for theme in THEMES:
        fails = report[f"contrast-{theme}"]["contrast"]
        print(f"  [{theme}] 对比度不达标 {len(fails)} 处")
        for item in fails[:5]:
            print(f"      {item['got']}:1 (需 {item['need']}) {item['size']}px "
                  f"{item['sel']} 「{item['text']}」")
    desktop = report["desktop-1440"]
    print(f"  字号组合数        {desktop['typeSizeCount']}  (健康系统 6–10)")
    print(f"  画布外小触控目标  {len(desktop['small'])} 个  (< 24px)")
    squeezed = [b for b in desktop["badges"] if b["w"] <= b["h"]]
    print(f"  被挤压成竖排的徽标 {len(squeezed)} 个")
    for name, _, _ in VIEWPORTS:
        print(f"  [{name}] 小触控目标 {len(report[name]['small'])} 个")
    print(f"  页面 JS 错误      {len(errors)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
