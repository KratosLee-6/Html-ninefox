"""Capture the five core workbench views for a release tag.

These five (paper / night / tablet / mobile / template sidebar) were shot by
hand for v0.6.0 and have no capture script, so a v0.6.1 release that reuses
them ships screenshots whose top-bar badge reads v0.6.0. That is a false
claim about what the attachment shows, so they are recorded for real instead.

The other eighteen views come from the two evidence gates and are already
regenerated per tag. This script covers the gap, and asserts the badge before
saving, so a stale capture cannot pass silently again.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/screenshots/v0.6.1"
BASE = "http://127.0.0.1:8636"
EXPECTED = "v0.6.1"


def snap(page, name: str) -> None:
    """Screenshot, then prove the top-bar badge matches the tag.

    Checking after the save is deliberate: the check has to apply to the file
    that actually landed on disk, not to a state the page was in earlier.
    """
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path))
    badge = page.inner_text("#ver").strip()
    if badge != EXPECTED:
        raise SystemExit(f"{name}: badge reads {badge!r}, expected {EXPECTED!r}")
    print(f"  {name:26} badge {badge}  {path.stat().st_size // 1024} KB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        assert page.inner_text("#ver").strip() == EXPECTED, "wrong version"

        # paper (the default theme)
        snap(page, "workbench-paper-1440")
        snap(page, "workbench-overview")

        # template library — the first sidebar tab is 版式
        page.click('.tabs button:has-text("版式")') if page.is_visible(
            '.tabs button:has-text("版式")') else None
        page.wait_for_timeout(700)
        snap(page, "sidebar-templates")

        # night theme via the real toggle, not by injecting a class
        page.click("#btn-theme")
        page.wait_for_timeout(900)
        snap(page, "workbench-night-1440")
        page.click("#btn-theme")
        page.wait_for_timeout(700)

        # responsive viewports
        for w, h, name in ((768, 1024, "workbench-tablet-768"),
                           (390, 844, "workbench-mobile-390")):
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(1100)
            snap(page, name)

        browser.close()
    print(f"\n{len(list(OUT.glob('*.png')))} shots in {OUT.name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
