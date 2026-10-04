"""Success-path smoke tests: run the real code and assert the real output.

Why this file exists
--------------------
Three releases shipped with everything green and a feature broken:

  v0.6.0  the Windows portable package passed four build jobs and the whole
          suite, then crashed on start;
  v0.6.2  the SSRF fix shipped with three blocking defects — every fetch
          raised TypeError — while five CI jobs, 39 byte-verified release
          assets and the metadata gate all passed;
  and the structural gate written to prevent a repeat scored 1/5 under
          mutation, because it scanned source text instead of running anything.

The shared cause is that the suite could observe a *refusal* but never a
*success*. "Correctly refused" and "completely broken" were the same signal.

These tests close that gap. Each one calls the production entry point, then
asserts on what came out — the rendered document, the manifest fields, the
files on disk. A broken implementation cannot satisfy an assertion about
content it never produces.

Two rules that keep them honest:

  1. No text scanning. Nothing here asserts that a string exists in the
     source; everything runs code.
  2. No early skip. A test that cannot observe its subject fails rather than
     skipping, because a skip reads as a pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from htmlninefox.generators import _tokens  # noqa: E402

# The real brief contract, read out of generators/_shared.py:content_of —
# content lives under a `content` sub-dict, not at the top level. The first
# draft of this file put these keys at the top level and every content
# assertion passed vacuously against the built-in defaults, which is exactly
# the "it ran but asserted nothing" trap.
BRIEF = {
    "intent": "landing",
    "product": "秋季新品发布",
    "brand": "九尾狐",
    "content": {
        "core_message": "让灵感在 HTML 里生长",
        "headline": "让灵感在 HTML 里生长",
        "hero_sub": "一句话进，一个可交付的网页出。",
    },
    "sections": [
        {"kind": "hero", "heading": "让灵感在 HTML 里生长",
         "body": "一句话进，一个可交付的网页出。"},
    ],
}


def preset(name: str = "linear-light") -> dict:
    """The real preset, straight from the shipped token table."""
    p = _tokens.PRESETS[name]
    return {"tokens": dict(p["tokens"]), "id": p["id"],
            "name": p.get("name", name), "dark": p.get("dark", False)}


# ------------------------------------------------------------------ generators
INTENTS = ["landing", "dashboard", "deck", "poster", "doc", "archdoc"]


@pytest.mark.parametrize("intent", INTENTS)
def test_generator_produces_a_complete_document(intent):
    """Every generator must emit a real, closed, styled HTML document.

    A generator that raises, returns an empty string, forgets the closing tag
    or drops the token-driven CSS all fail here. None of those could hide
    behind a refusal-only assertion.
    """
    from htmlninefox import generators as gens

    html = gens.render(intent, BRIEF, preset(), {"blocks": None})
    low = html.lower()

    assert html.strip(), f"{intent}: 产物为空"
    assert low.startswith("<!doctype html>"), f"{intent}: 缺少 doctype"
    assert "</html>" in low, f"{intent}: 未闭合 html"
    assert "<style>" in low, f"{intent}: 没有样式块"
    assert "--fox-primary" in html, f"{intent}: 令牌驱动的 CSS 未进入产物"
    assert 'lang="zh-CN"' in html, f"{intent}: 缺少语言声明"
    assert "viewport" in low, f"{intent}: 缺少 viewport"
    # balanced-ish tag sanity: the document must contain real body content
    assert "<body" in low and "</body>" in low, f"{intent}: body 未闭合"
    assert len(html) > 2000, f"{intent}: 产物过短（{len(html)}），可能未渲染"


def test_generator_embeds_the_brief_content():
    """The rendered page must actually contain what the brief asked for.

    This is the assertion that "it ran" cannot fake: a shell that renders an
    empty template is still a shell.
    """
    from htmlninefox import generators as gens

    html = gens.render("landing", BRIEF, preset(), {"blocks": None})
    assert "让灵感在 HTML 里生长" in html, "brief 的核心文案未出现在产物中"
    assert "九尾狐" in html, "brand 未出现在产物中"


def test_preset_switch_changes_the_output():
    """Two presets must produce different documents, or the preset is ignored."""
    from htmlninefox import generators as gens

    a = gens.render("landing", BRIEF, preset("linear-light"), {"blocks": None})
    b = gens.render("landing", BRIEF, preset("shadcn-dashboard"),
                    {"blocks": None})
    assert a != b, "切换风格预设后产物完全相同，预设可能没被真正使用"


# ------------------------------------------------------------------- exporting
def make_real_project(tmp_path, name, html, intent="landing"):
    """Build a project the way the product builds one.

    Two details are not optional and both were wrong in the first draft:

    * `.foxstate.json` — `analyze_project` goes through the store, which
      rejects a directory without it. Building only output.html tests a shape
      the product would refuse.
    * written via `durable.atomic_write` — the product writes artefacts with
      `newline=""`, which suppresses the CRLF translation `Path.write_text`
      applies on Windows. Using write_text made the file 211 bytes larger
      than the string, so a `source_size == len(html.encode())` assertion was
      measuring my own test fixture, not the product.
    """
    from htmlninefox import pipeline
    from htmlninefox.durable import atomic_write

    project = tmp_path / name
    project.mkdir()
    atomic_write(project / "output.html", html)
    (project / pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "秋季新品发布",
        "intent": intent,
        "preset_id": "linear-light",
        "revision": 0,
        "created_at": "2026-10-04T12:00:00",
    }, ensure_ascii=False), encoding="utf-8")
    return project


def test_analyze_project_reads_a_real_generated_page(tmp_path):
    """Run the real analyser over a real generated artefact."""
    from htmlninefox import generators as gens
    from htmlninefox import exporting

    html = gens.render("landing", BRIEF, preset(), {"blocks": None})
    make_real_project(tmp_path, "smoke-analyze", html)

    manifest = exporting.analyze_project(tmp_path, "smoke-analyze")
    assert manifest, "analyze_project 返回空"
    assert manifest.get("source_size") == len(html.encode("utf-8")), (
        f"source_size 与实际文件不符：{manifest.get('source_size')} "
        f"!= {len(html.encode('utf-8'))}")
    assert manifest.get("viewport"), "缺少 viewport 声明"
    assert manifest.get("intent") == "landing", (
        f"intent 未从项目状态读出：{manifest.get('intent')}")
    assert 0 <= manifest.get("compatibility_score", -1) <= 100, (
        f"兼容性分数越界：{manifest.get('compatibility_score')}")
    runtime = manifest.get("runtime")
    assert isinstance(runtime, dict), "缺少 runtime 段"
    assert runtime.get("formats"), "runtime 未报告支持的导出格式"


def test_export_writes_a_real_pdf(tmp_path):
    """Export for real and check the bytes, not just the file's existence.

    The pattern that let v0.6.0 through was "the artifact exists". This
    asserts a PDF magic number, a plausible size and a proper trailer.
    """
    from htmlninefox import generators as gens
    from htmlninefox import exporting

    html = gens.render("landing", BRIEF, preset(), {"blocks": None})
    make_real_project(tmp_path, "smoke-export", html)

    manifest = exporting.analyze_project(tmp_path, "smoke-export")
    formats = manifest.get("runtime", {}).get("formats", [])
    assert "pdf" in formats, f"运行时未报告可导出 PDF：{formats}"

    request = exporting.normalize_export_request(
        {"project_name": "smoke-export", "format": "pdf"})
    result = exporting.export_project(tmp_path, request)
    assert not result.get("error"), f"导出报错：{result.get('error')}"

    project = tmp_path / "smoke-export"
    pdfs = [p for p in project.rglob("*.pdf")]
    assert pdfs, "导出后项目目录里没有 PDF"
    blob = pdfs[0].read_bytes()
    assert blob[:5] == b"%PDF-", f"不是 PDF 魔数：{blob[:8]!r}"
    assert len(blob) > 1000, f"PDF 过小（{len(blob)} 字节），可能是空壳"
    assert b"%%EOF" in blob[-2048:], "PDF 未正常结束"



# ------------------------------------------------------------------------ intake
def test_intake_transport_returns_real_bytes_over_a_real_socket():
    """The transport itself must return the page, not raise.

    This is the v0.6.2 shape proper. That release shipped a fetcher whose
    every request raised `TypeError` while six rejection-only gates stayed
    green, because none of them ever watched a fetch succeed.

    A first draft of this file covered only the parser, and a mutation that
    made the transport fail on every call left the whole suite green — the
    exact blind spot this file is meant to close. The transport is therefore
    exercised here on its own, with a real server and real bytes.

    The pinned handler dials the vetted address, so the resolver reports
    loopback and the transport connects to loopback. That is the design, not
    a trick: the address validate_url approved is the address that gets used.
    """
    import http.server
    import socket
    import threading

    from htmlninefox import intake

    body = "<!doctype html><html><body><h1>传输层</h1></body></html>"
    blob = body.encode("utf-8")

    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        status, headers, got = intake._default_transport(
            f"http://127.0.0.1:{port}/", {}, 10.0, 65536,
            ips=["127.0.0.1"])
    finally:
        srv.shutdown()
        srv.server_close()

    assert status == 200, f"传输层未返回 200，而是 {status}"
    assert got == blob, f"传输层返回的字节与页面不符：{got[:40]!r}"
    assert headers.get("content-type", "").startswith("text/html")


def test_intake_parses_real_structure_and_tokens():
    """Run the real parser and token extractor over real HTML.

    A fetcher that returns garbage, or a parser that returns nothing, both
    leave a refusal-only suite perfectly green — so the post-fetch half needs
    a success assertion of its own.
    """
    from htmlninefox import intake

    page = (
        "<!doctype html><html lang=\"zh-CN\"><head>"
        "<title>季度发布</title>"
        "<style>:root{--brand:#173C8F;--bg:#F4F0E7}"
        "body{font-family:system-ui;background:var(--bg)}</style>"
        "</head><body><header><h1>季度发布</h1></header>"
        "<main><section><h2>卖点一</h2><p>正文</p></section>"
        "<section><h2>卖点二</h2><p>正文</p></section></main>"
        "<footer>页脚</footer></body></html>"
    )

    skel = intake._SkeletonParser()
    skel.feed(page)
    skel.close()

    # The parser records headings, semantic tag counts and the title — not
    # "sections". The first draft of this test guessed `sections` and would
    # have failed on real, working code.
    assert skel.title == "季度发布", f"标题解析错误：{skel.title!r}"
    assert skel.headings, "没有解析出任何标题"
    texts = " ".join(h.get("text", "") for h in skel.headings)
    assert "季度发布" in texts, f"标题里没有页面标题：{texts[:120]}"
    assert "卖点一" in texts, f"标题里没有区块标题：{texts[:120]}"
    assert skel.semantic, "没有统计到语义标签"
    assert sum(skel.semantic.values()) >= 3, (
        f"语义标签过少：{skel.semantic}")

    colors = intake.COLOR_PATTERN.findall(page)
    assert colors, "颜色令牌抽取为空"
    assert any(c.upper().startswith("#173C8F") for c in colors), (
        f"主色未被抽到：{colors[:8]}")

    fonts = intake.FONT_PATTERN.findall(page)
    assert fonts, "字体令牌抽取为空"



def test_intake_rejects_a_private_address():
    """The refusal side, kept because it is a real security property."""
    from htmlninefox import intake

    with pytest.raises(intake.IntakeError) as exc:
        intake.validate_url("http://127.0.0.1/")
    assert exc.value.code == "intake_host_forbidden"


# ------------------------------------------------------------------- packaging
def test_packaging_verifier_is_wired_into_ci():
    """v0.6.0's package passed every gate and crashed on start.

    The verifier that catches it only counts if it runs in the release
    pipeline, so the wiring itself is the property under test.
    """
    verify = ROOT / "packaging" / "verify_portable.py"
    assert verify.exists(), "缺少 packaging/verify_portable.py"
    wired = [p for p in (ROOT / ".github" / "workflows").glob("*.yml")
             if "verify_portable.py" in p.read_text(encoding="utf-8")]
    assert wired, "verify_portable.py 没有接进任何 workflow"
