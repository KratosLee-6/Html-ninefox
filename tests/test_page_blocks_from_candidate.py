"""A candidate's sections must be able to become a project's, under copyright.

The channel exists: composition["blocks"] carries structured blocks through the
pipeline and doc.py renders them. What was missing is the last hop — turning what
intake already extracted from a page into those blocks — and the rule that says
when page text may be carried at all.

extract_components already slices a page into {tag, class, text_head, snippet},
but only for candidates whose source kind is "components", which is one of
thirteen built-in sources. The stored body is always there though, and the
extractor only reads html_text, so the slices can be re-derived on demand rather
than bloating every candidate.json.

The rule is per field, not per page. Structure, layout and palette are learnable
from almost any page; the prose is not. LICENSE_CLASSES is three-valued and the
existing check is whole-page — an inspiration-only candidate simply cannot enter
the template gallery at all. Carrying sections needs the finer grain:

    structure_only   what the page is made of, with none of its words
    verbatim         the page's own text, only when license_class == "open"

So a non-open page still yields structure; it just yields no content. And because
sections_of only returns blocks that have content, a structure-only page falls
back to the renderer's own copy — which is the correct outcome, not a silent
hole.

The gate below is written first: it is red on today's code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import intake  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE = """
<html><body>
  <header class="site-head"><h1>季度报告</h1><p>华东区 2026 上半年</p></header>
  <main>
    <section class="hero"><h2>本期要点</h2><p>营收同比增长百分之十二。</p></section>
    <section class="pricing"><h2>定价</h2><p>基础版每月 0 元，专业版每月 99 元。</p></section>
    <section class="faq"><h2>常见问题</h2><p>支持随时取消。</p></section>
  </main>
  <footer class="site-foot"><p>版权所有</p></footer>
</body></html>
"""

CANDIDATE = {
    "candidate_id": "c-1",
    "title": "某季度报告",
    "url": "https://example.com/report",
    "final_url": "https://example.com/report",
    "license_class": "open",
    "kind": "gallery",
}


def _blocks(license_class: str = "open") -> list[dict]:
    candidate = {**CANDIDATE, "license_class": license_class}
    return intake.page_blocks_from_candidate(candidate, PAGE)


def test_slices_can_be_re_derived_from_the_stored_body() -> None:
    """The extractor is re-run against the body the candidate already has.

    This is what lets a gallery candidate — which never had components
    extracted, because its source kind is not "components" — still contribute
    sections.
    """
    blocks = _blocks()
    assert blocks, "从候选已存的 body 没能切出任何分区"
    tags = {b["source_tag"] for b in blocks}
    assert {"header", "section", "footer"} <= tags, \
        f"语义标签没被认出来，切出来的是 {tags}"


def test_blocks_carry_what_a_renderer_needs_and_where_they_came_from() -> None:
    """id / kind / heading / content / provenance / source_url / ordinal.

    `kind` is what doc.py branches on; without it the block is dead weight in
    the channel. `ordinal` keeps the page's own order, which is the one thing
    about a page's structure that is genuinely worth keeping.
    """
    blocks = _blocks()
    for i, block in enumerate(blocks):
        assert block["id"], f"第 {i} 个分区没有 id"
        assert block["kind"] == "sections", \
            f"第 {i} 个分区的 kind 是 {block['kind']!r}，doc.py 只会渲染 sections"
        assert block["ordinal"] == i, f"第 {i} 个分区的序号是 {block['ordinal']}"
        assert block["source_url"], "分区没有记录来源 URL"
        assert block["heading"], f"第 {i} 个分区没有标题"
        assert block["content"], f"第 {i} 个分区没有内容"


def test_document_order_is_preserved() -> None:
    """A page's section order is structure, and it is the one thing about
    layout that survives being re-rendered by a different engine.

    Matched by substring rather than equality: `heading` is the section's
    visible text, so the header's heading is "季度报告 华东区 2026 上半年",
    not the bare <h1>.
    """
    headings = [b["heading"] for b in _blocks()]
    positions = []
    for wanted in ("季度报告", "本期要点", "定价", "常见问题", "版权所有"):
        found = [i for i, h in enumerate(headings) if wanted in h]
        assert found, f"页面里没有「{wanted}」这一节，切出来的是 {headings}"
        positions.append(found[0])
    assert positions == sorted(positions), \
        f"分区顺序丢了：{positions} 对应 {headings}"


def test_text_is_carried_verbatim_only_for_an_open_licensed_page() -> None:
    """The whole point. A page you may not copy gives structure, not prose."""
    open_blocks = _blocks("open")
    assert any(b["provenance"] == "verbatim" for b in open_blocks), \
        "open 许可的页面没有产出 verbatim 分区"
    assert any("基础版每月 0 元" in b["content"] for b in open_blocks), \
        f"open 许可的页面正文没有带过来：{open_blocks}"

    for licence in ("reference", "inspiration-only"):
        blocks = _blocks(licence)
        assert blocks, f"{licence} 许可的页面连结构都没有产出——不该"
        assert all(b["provenance"] == "structure_only" for b in blocks), \
            f"{licence} 许可的页面里有分区被标成 verbatim：" \
            f"{[b for b in blocks if b['provenance'] != 'structure_only']}"
        assert all(not b["content"] for b in blocks), \
            f"{licence} 许可的页面把原文带了出来：" \
            f"{[b for b in blocks if b['content']]}"


def test_a_structure_only_page_yields_nothing_the_renderers_would_use() -> None:
    """Structure-only blocks carry no content, and the renderer's structured
    reader only returns blocks that do. So the renderer falls back to its own
    copy — the correct outcome rather than a document with holes."""
    from htmlninefox.generators import _shared

    structure_only = [
        {"id": b["id"], "kind": b["kind"], "heading": b["heading"],
         "content": b["content"], "provenance": b["provenance"]}
        for b in _blocks("inspiration-only")
    ]
    assets = {"blocks": structure_only}
    assert _shared.blocks_of(assets) == [b["id"] for b in structure_only], \
        "渲染器的成员判断看不到这些分区的 id"
    assert _shared.sections_of(assets) == [], \
        "无内容的分区竟然被 sections_of 当成了可渲染内容——" \
        "渲染器会渲染出一堆空 section"


def test_a_page_with_no_recognisable_sections_yields_nothing() -> None:
    """No sections is a normal outcome, not an error."""
    assert intake.page_blocks_from_candidate(
        {**CANDIDATE}, "<html><body><p>just a paragraph</p></body></html>") == []


def test_blank_bodies_and_missing_fields_do_not_raise() -> None:
    """The endpoint takes user data off disk; it must not 500 on odd input."""
    for body in ("", "<html>", "<html><body>"):
        assert intake.page_blocks_from_candidate(CANDIDATE, body) == []
    assert intake.page_blocks_from_candidate({"candidate_id": "x"}, PAGE) or True


# --------------------------------------------------------------- the endpoint


class _ApprovedCandidate:
    """The one thing page-blocks needs that a plain dict cannot give it: a
    candidate store whose body can be read back, since the slices are re-derived
    from the stored HTML rather than from whatever the candidate happens to
    carry."""

    def __init__(self, candidate: dict, body: bytes) -> None:
        self._candidate = candidate
        self._body = body

    def get(self, candidate_id: str) -> dict:
        return dict(self._candidate)

    def body(self, candidate_id: str) -> bytes:
        return self._body


def _handler(candidate: dict, body: bytes = PAGE.encode("utf-8")):
    """The request handler with only its two collaborators swapped out."""
    from htmlninefox.server import app as server_app

    handler = object.__new__(server_app._Handler)
    handler._intake_candidates = lambda: _ApprovedCandidate(candidate, body)
    return handler


def test_the_endpoint_refuses_a_candidate_that_was_not_approved() -> None:
    """Same rule as the style-preset endpoint next to it: taking a page apart is
    something you do to a page you accepted."""
    from htmlninefox.server import app as server_app

    handler = _handler({**CANDIDATE, "status": "pending"})
    with pytest.raises(server_app.StoreError) as error:
        handler._api_intake_page_blocks({"candidate_id": "c-1"})
    assert error.value.code == "intake_candidate_not_approved"


def test_the_endpoint_reports_whether_text_came_along() -> None:
    """The caller has to be able to tell "structure only" from "with prose"
    without re-deriving the licence rule themselves."""
    for licence, expected in (("open", True), ("reference", False),
                              ("inspiration-only", False)):
        handler = _handler({**CANDIDATE, "status": "approved",
                            "license_class": licence})
        out = handler._api_intake_page_blocks({"candidate_id": "c-1"})
        assert out["license_class"] == licence
        assert out["carries_text"] is expected, \
            f"{licence} 的 carries_text 应为 {expected}"
        assert out["blocks"], f"{licence} 至少应产出结构"


def test_the_endpoint_does_not_save_blocks_into_the_candidate() -> None:
    """The blocks are a proposal, not a decision. Persisting them would make
    carrying a page's text a side effect of fetching it."""
    handler = _handler({**CANDIDATE, "status": "approved"})
    out = handler._api_intake_page_blocks({"candidate_id": "c-1"})
    assert "components" not in out["candidate"], \
        "端点把分区写回了候选——用户还没决定要不要，就先存上了"
    assert "blocks" not in out["candidate"]


def test_blocks_survive_the_pipeline_and_reach_the_page() -> None:
    """The end-to-end half: blocks built from a page's own sections come out in
    the generated document."""
    import tempfile

    from htmlninefox import pipeline

    blocks = _blocks("open")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        pipeline.run_expert(
            "写一份季度报告", output=str(out), quiet_llm=True,
            intent_override="doc",
            composition={"blocks": blocks, "selection_mode": "page"})
        project = next(p for p in out.iterdir() if p.is_dir())
        state = json.loads((project / pipeline.STATE_FILE).read_text(encoding="utf-8"))
        stored = state["assets"]["blocks"]
        assert [b["heading"] for b in stored] == [b["heading"] for b in blocks], \
            f"分块在 .foxstate.json 里变了形：{stored}"
        html = (project / "output.html").read_text(encoding="utf-8")
        for wanted in ("季度报告", "本期要点", "定价", "常见问题"):
            assert wanted in html, f"页面自己的分区「{wanted}」没出现在产物里——通道通了但没人消费"
        at = [html.index(w) for w in ("季度报告", "本期要点", "定价", "常见问题")]
        assert at == sorted(at), f"产物里分区的顺序和页面上的不一样：{at}"