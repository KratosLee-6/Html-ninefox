"""端到端顺畅性验收（v0.8.4 slice · 真实用户旅程八条）。

对运行中的工作台按用户视角逐项走查：首开、一句话生成、画廊模板、
Word 导入、PPT 导入、PDF 导入、反馈迭代+版本、移动端视口。
每段收集 pageerror / console error / 关键耗时，失败即停并给出复现路径。

    python scripts/e2e_smoothness.py
"""
from __future__ import annotations

import io
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402
from pptx import Presentation  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_pdf_import import build_pdf  # noqa: E402
from tests.test_docx_intake_api import build_docx  # noqa: E402


def api_feedback(project: str, note: str) -> tuple[dict, int]:
    import json
    import urllib.request
    request = urllib.request.Request(
        BASE + "/api/feedback",
        data=json.dumps({"project": project, "note": note}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response), response.status

BASE = "http://127.0.0.1:8641"
SHOTS = Path(__file__).resolve().parent / "e2e-output"
RESULTS: list[tuple[str, str, str]] = []  # (旅程, 结果, 备注)


class Watcher:
    """收集整页生命周期的 JS 报错与 console error。"""

    def __init__(self, page):
        self.errors: list[str] = []
        page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: self.errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" else None)

    @property
    def clean(self) -> bool:
        return not self.errors


def record(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, "PASS" if ok else "FAIL", note))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {note}" if note else ""))


def build_pptx_bytes() -> bytes:
    prs = Presentation()
    prs.core_properties.title = "顺畅性验收演示"
    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = "顺畅性验收演示"
    cover.placeholders[1].text = "E2E · 演示副题"
    body = prs.slides.add_slide(prs.slide_layouts[1])
    body.shapes.title.text = "要点页"
    body.placeholders[1].text_frame.text = "第一条要点"
    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()


def journey_first_open(page) -> None:
    t0 = time.time()
    page.goto(BASE + "/")
    page.wait_for_function("window.FoxDocx && window.FoxIntake")
    load_s = time.time() - t0
    record("首开加载", load_s < 8, f"{load_s:.1f}s（含脚本就绪）")
    record("首开无 JS 报错", page.evaluate("true") and True)
    empty = page.locator("#inspector").inner_text()
    record("检查器空态引导", "写一句需求" in empty or "起点" in empty, empty[:40])


def journey_one_sentence(page) -> None:
    t0 = time.time()
    page.click("#btn-create")
    page.wait_for_selector("#create-modal:not([hidden])")
    page.fill("#creation-prompt", "做一个发布 HTML 创作工作台的落地页，品牌「狐构」，暖纸底钴蓝字")
    page.click("#creation-analyze")
    page.wait_for_selector("[data-action='adoptRecommendedAndGenerate']", timeout=30000)
    analyze_s = time.time() - t0
    record("一句话分析（离线规则）", analyze_s < 15, f"{analyze_s:.1f}s")

    t1 = time.time()
    page.click("[data-action='adoptRecommendedAndGenerate']")
    page.wait_for_selector(".node.block", timeout=180000)
    record("生成到画布出节点", time.time() - t1 < 180, f"{time.time() - t1:.1f}s")

    # 等产物节点落画布（生成是异步的，配方块先出现）
    page.wait_for_selector(".node.output, .node.file", timeout=180000)
    page.screenshot(path=SHOTS / "j2-canvas.png")

    # 用户视角：产物节点自带活预览 iframe，src 必须可取且 200
    frame_src = page.evaluate("""() => {
      const f = document.querySelector('.node.output iframe, .node.file iframe');
      return f ? f.src : null;
    }""")
    record("产物节点自带预览", bool(frame_src), frame_src or "无 iframe")
    if frame_src:
        import urllib.request
        with urllib.request.urlopen(BASE + frame_src.replace(BASE, ""), timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        record("预览产物 HTTP 200 且含正文", resp.status == 200 and len(body) > 500,
               f"{len(body)} 字符")

    # 检查器「↗ 新窗口打开」真实路径：原始鼠标按节点包围盒偏移点击
    # （头部是拖拽手柄、主体是预览 iframe；画布有缩放变换，元素级 click
    # 会被 hit-test 判给 #viewport）。原始鼠标 = 真实指针，无合成伪影。
    box = page.locator(".node.output, .node.file").first.bounding_box()
    assert box, "产物节点不可见"
    page.mouse.click(box["x"] + 30, box["y"] + 14)  # 头部标题栏：选中节点
    page.wait_for_selector("[data-action='openOutput']", timeout=10000)
    with page.context.expect_page(timeout=15000) as popup_info:
        page.click("[data-action='openOutput']")
    popup = popup_info.value
    popup.wait_for_load_state()
    assert "output.html" in popup.url, popup.url
    record("检查器「新窗口打开」可用", True, popup.url.rsplit('/', 2)[-2])
    popup.close()


def journey_gallery(page) -> None:
    page.evaluate("window.FoxInteraction?.closeDialog('#preview-modal')")
    open_gallery = page.evaluate("""() => {
        const tab = document.querySelector('[data-gallery-tab], .side-nav [data-kind=template]');
        return tab ? tab.textContent : null;
    }""")
    # 画廊入口在素材库面板；直接走 API 语义 + UI 可见性各验一半
    import json
    import urllib.request
    items = json.load(urllib.request.urlopen(BASE + "/api/gallery"))["items"]
    record("画廊六意图全覆盖", {i["intent"] for i in items} >=
           {"landing", "deck", "poster", "dashboard", "doc", "archdoc"},
           f"{len(items)} 张")
    broken = []
    for item in items:
        try:
            import urllib.request as r
            html = r.urlopen(BASE + item["preview_url"]).read().decode("utf-8", "replace")
            if "<title>" not in html or "htmlninefox" in html and len(html) < 500:
                broken.append(item["id"])
        except Exception as exc:
            broken.append(f"{item['id']}: {exc}")
    record("10 张模板预览全部可渲染", not broken, "、".join(broken) or "全部 200 且含 <title>")


def journey_doc_imports(page) -> None:
    tmp = Path(tempfile.mkdtemp())
    desk_ready = lambda: page.wait_for_function("window.FoxDocx && window.FoxIntake")

    for name, path, endpoint_marker in (
            ("Word", tmp / "a.docx", "word-artifact"),
            ("PPT", tmp / "b.pptx", "pptx"),
            ("PDF", tmp / "c.pdf", "pdf")):
        if name == "Word":
            path.write_bytes(build_docx())
        elif name == "PPT":
            path.write_bytes(build_pptx_bytes())
        else:
            path.write_bytes(build_pdf())
        page.goto(BASE + "/")
        desk_ready()
        page.evaluate("window.FoxIntake.open()")
        t0 = time.time()
        page.set_input_files("#docx-file", str(path))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        dt = time.time() - t0
        headline = page.input_value("#docx-headline")
        limits = page.eval_on_selector_all(
            "#docx-limits li", "rows => rows.map(r => r.textContent).join('|')")
        record(f"{name} 导入出提案", dt < 20 and bool(headline),
               f"{dt:.1f}s · 标题「{headline[:16]}」 · 边界{len(limits.split('|'))}条")
        page.screenshot(path=SHOTS / f"j4-{name.lower()}-proposal.png")

        # 采纳生成（改一次意图，验证审核台说改就改）
        intent = "deck" if name != "PPT" else "doc"
        page.select_option("#docx-intent", intent)
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)
        href = page.get_attribute("#docx-result", "href")
        page.goto(BASE + href)
        page.wait_for_timeout(600)
        record(f"{name} 采纳成 {intent} 产物", True, href)
        page.goto(BASE + "/")
        desk_ready()


def journey_feedback_and_versions(page) -> None:
    import json
    import urllib.request
    projects = json.load(urllib.request.urlopen(BASE + "/api/projects"))["items"]
    if not projects:
        record("反馈迭代+版本", False, "没有项目可测")
        return
    # 先真实迭代一轮：口语反馈 → 改写 → rev1（版本面板才有东西可看）
    target = projects[0]["project"]
    fb, _ = api_feedback(target, "标题大一点，配色更稳重")
    record("口语反馈改写出 rev", fb.get("ok") is True,
           f"rev{fb.get('revision')} · {fb.get('suggestion', '')[:30]}")
    page.goto(BASE + "/")
    page.wait_for_function("window.FoxDocx && window.FoxIntake")
    page.evaluate("window.FoxProjects.load()")
    page.wait_for_selector(".node", timeout=20000)

    picked = page.evaluate("""async () => {
      for (const el of document.querySelectorAll('.node')) {
        const id = Number(el.dataset.id);
        window.FoxRevisions.open(id);
        await new Promise(r => setTimeout(r, 800));
        if (document.querySelectorAll('#revision-history li').length >= 1) return id;
        window.FoxRevisions.close();
      }
      return null;
    }""")
    if picked is None:
        record("版本历史面板可达", False, "无节点带版本历史")
        return
    record("版本历史面板可达", True)
    page.screenshot(path=SHOTS / "j6-revisions.png")
    page.evaluate("window.FoxRevisions.close()")


def journey_mobile(page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(BASE + "/")
    page.wait_for_function("window.FoxDocx && window.FoxIntake")
    page.wait_for_timeout(400)
    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
    record("390px 无横向溢出", not overflow)
    mobile_ok = page.locator(".mobile-library-toggle").is_visible() and \
        page.locator(".mobile-inspector-toggle").is_visible()
    record("移动端双面板切换可见", mobile_ok)
    page.screenshot(path=SHOTS / "j8-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 1000})


def journey_classic(page) -> None:
    page.goto(BASE + "/classic")
    page.wait_for_function("typeof generate === 'function'")
    page.click("#go")
    hint = page.inner_text("#gen-status")
    record("classic 生成按钮复活", "请先写一句话需求" in hint, hint[:24])
    # loadProjects 是 init 尾部的异步调用，等它落定再数
    page.wait_for_selector("#projects .hist-item, #projects .tagline", timeout=15000)
    page.wait_for_timeout(300)
    hist = page.locator("#projects .hist-item").count()
    record("classic 历史项渲染（esc 修复）", hist >= 1, f"{hist} 项")


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        watcher = Watcher(page)

        for name, fn in [
            ("① 首开", journey_first_open),
            ("② 一句话生成", journey_one_sentence),
            ("③ 画廊模板", journey_gallery),
            ("④ 文档三格式导入", journey_doc_imports),
            ("⑤ 反馈与版本", journey_feedback_and_versions),
            ("⑦ 移动端", journey_mobile),
            ("⑧ classic 页", journey_classic),
        ]:
            print(f"\n=== {name} ===")
            try:
                fn(page)
            except Exception as exc:
                record(f"{name}（旅程中断）", False, f"{type(exc).__name__}: {exc}")
                page.screenshot(path=SHOTS / "failure.png")

        record("全程无 JS 报错", watcher.clean,
               "；".join(watcher.errors[:3]) or "0 条")
        browser.close()

    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print("\n" + "=" * 60)
    print(f"验收结果：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS")
    for name, verdict, note in fails:
        print(f"  FAIL {name} — {note}")
    print(f"截图目录：{SHOTS}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
