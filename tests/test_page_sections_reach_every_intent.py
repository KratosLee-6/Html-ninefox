"""A page's own sections must reach the page, in every intent.

Measured before the fix: landing rendered 0 body characters, archdoc 26 (its
shell alone), and dashboard/deck/poster silently shipped the built-in copy —
the page's prose simply did not appear. `doc` was the only intent that
consumed the block channel, so v0.7's headline feature was usable for one of
six content types while 526 tests stayed green.

These gates assert on rendered output, for every intent, two things:

  1. with page sections, the page's own prose is in the body;
  2. without them, the output is byte-identical to before — the built-in copy
     is a fallback, never something a page's content displaces partially.

The second half matters as much as the first. A "fix" that appends the page's
sections to the built-in copy would pass check 1 while quietly producing a
page that mixes someone else's prose with the template's.
"""

from __future__ import annotations

import re

import pytest

from htmlninefox.generators import _tokens, render

INTENTS = ["landing", "dashboard", "deck", "poster", "archdoc", "doc"]
BRIEF = {"brief": {"brand": "狐构", "headline": "把想法变成可交付的成果"}}
PRESET = dict(_tokens.get_preset(_tokens.DEFAULT_PRESET))

ALPHA = "PAGE_PROSE_ALPHA 独有的产品说明文字，必须出现在成品里。"
BETA = "PAGE_PROSE_BETA 独有的上手步骤说明，同样必须出现在成品里。"

PAGE_BLOCKS = [
    {"id": "page-section-1", "kind": "sections",
     "heading": "为什么选我们", "content": ALPHA},
    {"id": "page-section-2", "kind": "sections",
     "heading": "怎么开始", "content": BETA},
]


def body_of(html: str) -> str:
    m = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    assert m, f"no <body> in output:\n{html[:400]}"
    return m.group(1)


@pytest.mark.parametrize("intent", INTENTS)
def test_page_prose_reaches_the_rendered_page(intent):
    out = render(intent, BRIEF, PRESET, {"blocks": PAGE_BLOCKS})
    body = body_of(out)
    assert ALPHA in body, f"{intent} dropped the first page section"
    assert BETA in body, f"{intent} dropped the second page section"


_BUILTIN_MARKERS = {
    "landing": ["为真实工作流而生", "数据安全如何保障？", "三步接入，即刻提效"],
    "dashboard": ["数据概览", "本周访问趋势", "最近订单"],
    "deck": ["今天的问题", "数字说话", "路线图", "谢谢观看"],
    "poster": ["ANNOUNCING", "立即扫码报名"],
    "archdoc": ["系统分层", "生成流水线", "组件清单", "关键决策"],
    "doc": ["背景与目标", "方案与路径", "风险与对策"],
}

# `doc` is the one intent that was already consuming the block channel, and it
# does so per-branch: the page replaces the "sections" and "key_points" copies
# and leaves the document's own title, summary, table and conclusion in place.
# That is its long-standing design, not a regression, so it is excluded from
# the "page content replaces the built-in copy" rule below rather than being
# forced into a shape it never had.
_REPLACES_BUILTIN_COPY = [i for i in INTENTS if i != "doc"]


@pytest.mark.parametrize("intent", _REPLACES_BUILTIN_COPY)
def test_page_prose_replaces_the_built_in_copy(intent):
    """A page's content must not be pasted onto the template's product.

    Every renderer has unmistakable strings of its own. If any survive
    alongside the page's prose, the output is a hybrid — someone else's words
    welded onto the template's product, which is worse than either alone,
    because it looks delivered.
    """
    body = body_of(render(intent, BRIEF, PRESET, {"blocks": PAGE_BLOCKS}))
    for marker in _BUILTIN_MARKERS[intent]:
        assert marker not in body, (
            f"{intent} kept its built-in copy ({marker!r}) alongside the "
            f"page's own content — the two must not be mixed")


@pytest.mark.parametrize("intent", INTENTS)
def test_page_prose_appears_exactly_once(intent):
    """A section rendered twice is a visible defect, so count, don't just test."""
    body = body_of(render(intent, BRIEF, PRESET, {"blocks": PAGE_BLOCKS}))
    assert body.count(ALPHA) == 1, f"{intent} rendered the first section {body.count(ALPHA)} times"
    assert body.count(BETA) == 1, f"{intent} rendered the second section {body.count(BETA)} times"


def test_doc_keeps_its_own_structure_around_the_page():
    """doc's contract: page sections replace two blocks, not the whole page.

    A single test rather than a parametrized skip. Five skipped cases look
    like coverage in a summary line while asserting nothing, and a permanently
    skipping gate is worse than no gate.
    """
    body = body_of(render("doc", BRIEF, PRESET, {"blocks": PAGE_BLOCKS}))
    assert "文档" in body, "doc lost its document frame"
    assert ALPHA in body and BETA in body
    # The sections the page does not speak to are still the document's own.
    assert "摘要" in body, "doc dropped its summary around the page's sections"


@pytest.mark.parametrize("intent,vocabulary,expected,absent", [
    ("landing", ["hero"], ["把想法变成可交付的成果"], ["数据安全如何保障？", "最近订单"]),
    ("dashboard", ["charts"], ["本周访问趋势"], ["最近订单", "数据概览"]),
    ("deck", ["cover", "metrics"], ["数字说话"], ["路线图", "谢谢观看"]),
    ("poster", ["headline"], ["ANNOUNCING"], ["立即扫码报名"]),
    ("archdoc", ["flow"], ["生成流水线"], ["系统分层", "组件清单"]),
    ("doc", ["summary"], ["摘要"], ["背景与目标", "系统分层"]),
])
def test_plain_id_blocks_still_select_exactly_what_they_name(intent, vocabulary,
                                                              expected, absent):
    """Every pre-existing project passes plain id blocks and must not change.

    Two things at once, because they fail in opposite directions: the ids that
    WERE asked for must appear, and the ones that were NOT must stay absent.
    Asserting only the first would let a renderer drift back to "render
    everything"; asserting only the second would miss content going missing.

    The ids come from each renderer's own vocabulary. A shared probe such as
    ["hero", "features"] is meaningless for a renderer that has never heard of
    them, and asserting on it turns an unrelated question into a false failure.
    """
    body = body_of(render(intent, BRIEF, PRESET, {"blocks": vocabulary}))
    for probe in (ALPHA, BETA):
        assert probe not in body, f"{intent} invented page content"
    for marker in expected:
        assert marker in body, f"{intent} lost the requested block {marker!r}"
    for marker in absent:
        assert marker not in body, (
            f"{intent} rendered {marker!r} although it was not requested")


@pytest.mark.parametrize("intent", INTENTS)
def test_structure_only_page_falls_back_to_the_built_in_copy(intent):
    """A page that carries structure but no prose must not render blank.

    `sections_of` drops blocks without content, so a structure-only page —
    which is what every non-open licence produces — looks exactly like a page
    with no blocks at all. That is the intended fallback, and it is asserted
    here so a future "optimisation" of the gate cannot turn it into a blank
    page for reference-licensed sources.
    """
    structure_only = [
        {"id": "page-section-1", "kind": "sections", "heading": "标题", "content": ""},
        {"id": "page-section-2", "kind": "sections", "heading": "小节", "content": ""},
    ]
    body = body_of(render(intent, BRIEF, PRESET, {"blocks": structure_only}))
    assert len(body.strip()) > 40, f"{intent} rendered blank for a structure-only page"
    for marker in _BUILTIN_MARKERS[intent]:
        assert marker in body, f"{intent} lost its built-in copy for a structure-only page"


@pytest.mark.parametrize("intent", INTENTS)
def test_no_blocks_at_all_keeps_every_built_in_marker(intent):
    body = body_of(render(intent, BRIEF, PRESET, {}))
    for marker in _BUILTIN_MARKERS[intent]:
        assert marker in body, f"{intent} lost {marker!r} with no blocks at all"


# ------------------------------------------------------ the endpoint's shape

_ENDPOINT_PAGE = """
<html><body><main>
  <section class="hero"><h1>狐构·把想法变成可交付的成果</h1>
    <p>PAGE_PROSE_ALPHA 独有的产品说明文字，必须出现在成品里。</p>
  </section>
  <section class="features"><h2>为什么选我们</h2>
    <p>容器自己的说明文字。</p>
    <section class="nested"><h3>怎么开始</h3>
      <p>PAGE_PROSE_BETA 独有的上手步骤说明，同样必须出现在成品里。</p>
    </section>
  </section>
</main></body></html>
"""


@pytest.mark.parametrize("intent", INTENTS)
def test_blocks_from_the_real_endpoint_render_each_prose_once(intent):
    """The blocks must arrive the way `/api/intake/page-blocks` actually builds
    them — heading from the section's own heading tag, content the prose below
    it — and the prose must appear exactly once per document.

    The hand-made fixture above cannot see the shape this one covers: the real
    endpoint used to set heading = content = the section's text head, so every
    renderer printed each page's prose twice (once in the <h2>, once in the
    <p>) while these gates stayed green on blocks whose heading differed from
    their content. Same lesson as ever: exercise the producer's real shape, or
    the gate certifies a fixture instead of the feature.
    """
    from htmlninefox import intake

    candidate = {"candidate_id": "c-e2e", "title": "实测页",
                 "url": "https://example.com/page",
                 "final_url": "https://example.com/page",
                 "license_class": "open", "kind": "gallery"}
    blocks = intake.page_blocks_from_candidate(candidate, _ENDPOINT_PAGE)
    assert len(blocks) >= 2, f"端点形状的页面只切出 {len(blocks)} 个分区"
    body = body_of(render(intent, BRIEF, PRESET, {"blocks": blocks}))
    assert body.count("PAGE_PROSE_ALPHA") == 1, \
        f"{intent}: 第一段正文出现了 {body.count('PAGE_PROSE_ALPHA')} 次"
    assert body.count("PAGE_PROSE_BETA") == 1, \
        f"{intent}: 嵌套分区的正文出现了 {body.count('PAGE_PROSE_BETA')} 次"