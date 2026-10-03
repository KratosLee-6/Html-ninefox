"""Record a real, continuous operating session of the workbench.

The previous cut was rejected as "全靠截图介绍". It was factually built from
real states, but it *looked* like screenshots with a slow zoom: the cursor
never moved, characters never appeared one by one, nodes never popped in.
No viewer could tell it from a slideshow, and a promo that could pass for a
slideshow is not a demonstration.

So this records an actual session with Playwright's video recorder. Every
pixel comes from the live page while real input events are dispatched:

  - page.mouse.move before every click, so the cursor travels and lands
  - page.keyboard.type with per-character delay, so the text is typed
  - real waits between steps, so the viewer can read what happened
  - the generation actually runs server-side and the nodes actually appear

This is not H3. A text-to-video model cannot be used for the interface
footage: it renders Chinese as garbled glyphs, invents button positions and
draws edges that mean nothing. The one H3 clip in this project is usable
precisely because its prompt forbids all text. H3 stays on the abstract
opener; the demonstration itself is recorded, not generated.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Point at whichever workbench instance this run should film. Use a separate
# port AND a separate --output root per cut, otherwise a second recording
# inherits the first one's projects and the canvas fills with duplicates.
BASE = os.environ.get("FOX_DEMO_BASE", "http://127.0.0.1:8633")
OUT = ROOT / ".tmp/demo-run-video"
PROMPT = "做一个秋季新品发布落地页，含主视觉、卖点三条和报名表单"

# The English cut is a SEPARATE recording, not a translation of the same
# footage. The requirement is typed in English and the product is asked to
# analyse it for real, so the confidence it reports (72% here vs 67% for the
# Chinese prompt) is whatever it actually computed. Re-labelling the Chinese
# session would make the captions describe footage the product never
# produced.
#
# What cannot change is the interface language: the workbench ships in
# Chinese by default, so the UI stays Chinese in both cuts and the English
# cut carries English captions. The chips the analysis returns (落地页, 首页
# Hero) are the product's own output and are not rewritten either.
PROMPT_EN = ("Build an autumn product launch landing page with a hero, "
             "three selling points and a signup form")

W, H = 1920, 1080

# Start the workbench first, in a throwaway output root so a recording run
# never pollutes real projects:
#   python -m htmlninefox.cli serve --host 127.0.0.1 --port 8633 \
#       --output .tmp/demo-run

# Pacing, in seconds. These are not arbitrary: each one is long enough for a
# viewer to read what just happened, which is the difference between a demo
# and a slideshow.
BEAT = {
    "load": 2.2,
    "hover_create": 0.9,
    "open_panel": 2.0,
    "type": 0.085,      # per character
    "after_type": 1.6,
    "to_analyze": 0.9,
    "analyze_wait": 3.4,
    "read_analysis": 3.0,
    "to_adopt": 1.0,
    "generate_wait": 7.5,
    "settle": 3.0,
    "to_output": 1.4,
    "read_output": 2.8,
    "to_export": 1.4,
    "export_wait": 4.0,
    "read_export": 3.4,
}


def log(msg: str) -> None:
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def move_to(page, selector: str, jitter: bool = True) -> None:
    """Move the real cursor to an element's centre before acting on it."""
    box = page.eval_on_selector(
        selector,
        "e => { const r = e.getBoundingClientRect();"
        " return {x: r.x + r.width/2, y: r.y + r.height/2}; }")
    if jitter:
        box = {"x": box["x"] - 6, "y": box["y"] + 5}
    # Two-step move so the travel is visible rather than teleporting.
    page.mouse.move(box["x"] * 0.62, box["y"] * 0.72)
    page.wait_for_timeout(220)
    page.mouse.move(box["x"], box["y"], steps=18)
    page.wait_for_timeout(260)


def main() -> int:
    # `--lang en` records the English cut. Both cuts are real recordings; only
    # the typed requirement and the caption language differ.
    lang = "zh"
    if "--lang" in sys.argv:
        lang = sys.argv[sys.argv.index("--lang") + 1]
    if lang not in ("zh", "en"):
        raise SystemExit(f"unknown --lang {lang!r}")
    prompt = PROMPT_EN if lang == "en" else PROMPT
    suffix = "" if lang == "zh" else f"-{lang}"
    out_dir = OUT.parent / f"demo-run-video{suffix}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-device-scale-factor=1"])
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(out_dir),
            record_video_size={"width": W, "height": H},
            device_scale_factor=1)
        page = ctx.new_page()
        page.set_default_timeout(30000)

        # ---- 1. the workbench opens
        log("opening workbench")
        page.goto(BASE, wait_until="networkidle")
        assert page.inner_text("#ver").strip() == "v0.6.0"
        page.wait_for_timeout(int(BEAT["load"] * 1000))

        # ---- 2. cursor finds the create button
        log("cursor travels to 输入需求")
        move_to(page, "#btn-create")
        page.wait_for_timeout(int(BEAT["hover_create"] * 1000))
        page.click("#btn-create")
        page.wait_for_selector("#create-modal:not([hidden])")
        log("panel open")
        page.wait_for_timeout(int(BEAT["open_panel"] * 1000))

        # ---- 3. type the requirement, one character at a time
        # The English requirement is ~90 characters against the Chinese one's
        # 27, so it gets a slightly faster per-character delay to keep the
        # beat roughly the same length. Too fast and the viewer cannot follow
        # the words appearing, which is the whole point of typing it live.
        type_delay = BEAT["type"] * (0.72 if lang == "en" else 1.0)
        log(f"typing requirement ({lang}, {len(prompt)} chars)")
        move_to(page, "#creation-prompt")
        page.click("#creation-prompt")
        page.keyboard.type(prompt, delay=int(type_delay * 1000))
        assert page.input_value("#creation-prompt") == prompt
        log("typed in full")
        page.wait_for_timeout(int(BEAT["after_type"] * 1000))

        # ---- 4. real analysis
        log("clicking AI 分析并推荐")
        move_to(page, "#creation-analyze")
        page.click("#creation-analyze")
        page.wait_for_selector("#creation-analysis .analysis-chips span")
        page.wait_for_timeout(int(BEAT["analyze_wait"] * 1000))
        chips = page.eval_on_selector_all(
            "#creation-analysis .analysis-chips span",
            "els => els.map(e => e.textContent.trim())")
        log(f"analysis returned: {chips[:4]}")
        page.wait_for_timeout(int(BEAT["read_analysis"] * 1000))

        # ---- 5. adopt and generate — nodes really appear
        log("clicking 采用推荐并生成")
        move_to(page, "#creation-analysis button")
        before = page.eval_on_selector_all("#nodes .node", "e => e.length")
        page.click("#creation-analysis button")
        page.wait_for_function(
            f"() => document.querySelectorAll('#nodes .node').length > {before}")
        log(f"generation started ({before} nodes)")
        page.wait_for_timeout(int(BEAT["generate_wait"] * 1000))
        last = before
        for _ in range(30):
            page.wait_for_timeout(1000)
            n = page.eval_on_selector_all("#nodes .node", "e => e.length")
            if n == last:
                break
            last = n
        log(f"settled at {last} nodes")
        page.wait_for_timeout(int(BEAT["settle"] * 1000))

        # ---- 6. look at the generated artifact
        log("clicking the output node")
        box = page.eval_on_selector(
            "#nodes .node.output",
            "e => { const r = e.getBoundingClientRect();"
            " return {x: r.x + r.width/2, y: r.y + 18}; }")
        page.mouse.move(box["x"] * 0.6, box["y"] * 0.7)
        page.wait_for_timeout(240)
        page.mouse.move(box["x"], box["y"], steps=20)
        page.wait_for_timeout(420)
        page.mouse.click(box["x"], box["y"])
        log("output node focused")
        page.wait_for_timeout(int(BEAT["read_output"] * 1000))

        # ---- 7. open the export centre for real
        log("opening export centre")
        out_id = page.evaluate(
            "() => (nodes.find(n => n.kind === 'output') || {}).id")
        assert out_id is not None
        page.evaluate("(id) => window.FoxExports.open(id)", out_id)
        page.wait_for_selector("#export-modal:not([hidden])", timeout=20000)
        page.wait_for_function(
            "() => { const s = document.querySelector('#export-status');"
            " return s && /完成/.test(s.textContent); }", timeout=60000)
        score = page.evaluate(
            "() => window.FoxExports.draft().manifest.compatibility_score")
        log(f"export centre open, compatibility {score}")
        page.wait_for_timeout(int(BEAT["export_wait"] * 1000))
        page.wait_for_timeout(int(BEAT["read_export"] * 1000))

        # hold a beat on the conclusion, then stop
        page.wait_for_timeout(1200)
        ctx.close()
        browser.close()

    vids = sorted(out_dir.glob("*.webm"))
    if not vids:
        raise SystemExit("no video produced")
    src = vids[0]
    dst = out_dir / "session.webm"
    src.rename(dst)
    print(f"\nrecorded [{lang}]: {dst}  {dst.stat().st_size/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
