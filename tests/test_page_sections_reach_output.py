"""A page's sections must survive into the page the user generates.

`composition["blocks"]` is the channel the UI already uses to say which
sections a project has. Today it can only carry an id, and pipeline coerced
every entry with str() — so a structured block arrived downstream as its Python
repr. This is the channel that has to grow, not a new one.

Three properties, in order of how quietly they would fail:

  1. a structured block survives the pipeline intact
  2. the renderers' existing membership checks still work, because a dict
     block's id is still in `blocks_of`
  3. doc.py renders the page's own sections when they are there, and its
     hardcoded ones when they are not

The last one is the point. Without it the whole change would be plumbing that
produces nothing a user can see.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import pipeline  # noqa: E402
from htmlninefox.generators import _shared, _tokens, doc  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE_SECTIONS = [
    {"id": "sections", "kind": "sections", "heading": "定价",
     "content": "基础版每月 0 元，专业版每月 99 元。",
     "provenance": "verbatim"},
    {"id": "key_points", "kind": "key_points", "heading": "关键数字",
     "content": "上线 3 天，服务 1.2 万家企业。",
     "provenance": "verbatim"},
]

# Text that appears nowhere in doc.py's own copy, so finding it in the output can
# only mean the page's content got there.
FROM_PAGE = "基础版每月 0 元，专业版每月 99 元。"


def _preset() -> dict:
    """A real preset. base_css reads preset["tokens"], and the dispatcher always
    unpacks a preset before calling render — passing `{}` would be testing a
    call that cannot happen in production."""
    return _tokens.get_preset(_tokens.DEFAULT_PRESET)


def test_a_structured_block_survives_the_pipeline() -> None:
    """The bottleneck was one str() call. Structured blocks must pass through
    with their content intact, and their id preserved."""
    out = pipeline._normalize_blocks(list(PAGE_SECTIONS))
    assert len(out) == 2
    assert out[0]["heading"] == "定价", f"heading 丢了：{out[0]}"
    assert out[0]["content"] == PAGE_SECTIONS[0]["content"]
    assert out[0]["id"] == "sections", "id 没有留在 payload 里，下游拿不到"


def test_string_blocks_still_work_and_are_deduplicated() -> None:
    """Every project already on disk has string blocks, and there is no version
    field on .foxstate.json and no migration in load_state — so dropping string
    support would silently empty every existing project."""
    out = pipeline._normalize_blocks(["title", " summary ", "title", "", "doc"])
    assert out == ["title", "summary", "doc"], f"字符串形态的行为变了：{out}"


def test_blocks_that_are_neither_string_nor_dict_are_dropped() -> None:
    """str()'ing them produced something no renderer recognises, which is a
    section that silently disappears. Dropping them is at least visible."""
    out = pipeline._normalize_blocks(["title", 42, None, ["nested"], {"no_id": "x"}])
    assert out == ["title"], f"不该被接受的形态漏进来了：{out}"


def test_membership_checks_still_see_a_dict_block_s_id() -> None:
    """The 34 `if "x" in blocks` checks across the six renderers must keep
    working, or a page-derived project renders nothing at all."""
    assets = {"blocks": pipeline._normalize_blocks(list(PAGE_SECTIONS))}
    blocks = _shared.blocks_of(assets)
    assert "sections" in blocks, f"渲染器的成员判断看不到 dict 形态的 id：{blocks}"
    assert "key_points" in blocks
    assert "title" not in blocks


def test_the_sections_reader_returns_only_the_structured_ones() -> None:
    """A parallel reader, not a change to blocks_of: the six renderers depend on
    blocks_of meaning "ids", and that must not shift underneath them."""
    assets = {"blocks": pipeline._normalize_blocks(
        ["title"] + list(PAGE_SECTIONS))}
    assert _shared.blocks_of(assets) == ["title", "sections", "key_points"]
    sections = _shared.sections_of(assets)
    assert [s["heading"] for s in sections] == ["定价", "关键数字"], (
        f"sections_of 返回了 {sections}")
    assert sections[0]["provenance"] == "verbatim", "出处字段在传递中丢了"


def test_doc_renders_the_pages_own_sections_when_they_are_there() -> None:
    """The user-visible half. With page sections, doc.py shows them."""
    assets = {"blocks": pipeline._normalize_blocks(list(PAGE_SECTIONS))}
    html = doc.render({"brief": {"content": {"headline": "定价页"}}}, _preset(), assets)
    assert FROM_PAGE in html, (
        "页面自己的 section 文本没有出现在产物里——这条通道通了但没人消费它，"
        "整个改造就只是搬运")
    assert "定价" in html


def test_doc_falls_back_to_its_own_sections_when_there_are_none() -> None:
    """Existing projects have string blocks. Their output must not change."""
    assets = {"blocks": pipeline._normalize_blocks(
        ["title", "summary", "sections", "key_points", "table", "conclusion"])}
    html = doc.render({"brief": {"content": {"headline": "普通项目"}}}, _preset(), assets)
    # Copied from doc.py's own copy rather than written from memory: an earlier
    # version of this assertion used "关键路径", which appears nowhere in the
    # renderer, so it would have been asserting a string nobody ever produces.
    assert "方案与路径" in html, (
        "没有页面分块时，doc.py 自己的硬编码 section 消失了——"
        "既有项目的产物会被改变")
    assert "整体周期" in html and "关键交付物" in html, (
        f"没有页面分块时 key_points 的内置内容消失了：{html[-800:]}")


def test_a_page_section_does_not_suppress_the_built_in_copy_of_other_kinds() -> None:
    """A page will supply some kinds and not others.

    When it supplies `sections` but not `key_points`, and the project asked for
    both, the key points must still come from doc.py's own copy. Otherwise a
    partial page silently produces a document with a hole in it.
    """
    partial = [{"id": "sections", "kind": "sections", "heading": "定价",
                "content": FROM_PAGE, "provenance": "verbatim"}]
    assets = {"blocks": pipeline._normalize_blocks(["key_points"] + partial)}
    html = doc.render({"brief": {"content": {"headline": "部分分块"}}}, _preset(), assets)
    assert FROM_PAGE in html, "页面提供的 sections 没有出现"
    assert "整体周期" in html, (
        "页面没提供 key_points，doc.py 的内置要点也应该照常渲染，"
        "否则一个只提供部分分块的页面会产出一份有洞的文档")


def test_the_whole_shape_survives_a_real_generation(tmp_path) -> None:
    """End to end through run_expert, and then re-read the state: the sections
    must be in .foxstate.json, because re-render recomputes from state and
    anything not in it is lost on the next feedback or rerun."""
    out = tmp_path / "out"
    run = pipeline.run_expert(
        "写一份定价说明文档", output=str(out), quiet_llm=True, intent_override="doc",
        composition={"blocks": list(PAGE_SECTIONS), "selection_mode": "page"})
    project = Path(run["work"])
    state = json.loads((project / ".foxstate.json").read_text(encoding="utf-8"))
    stored = state["assets"]["blocks"]
    assert [b["content"] for b in stored] == [s["content"] for s in PAGE_SECTIONS], (
        f"分块没有进 .foxstate.json 的 assets.blocks：{stored}。"
        f"重渲染只用 state 里的四个字段，不在里面就会在下一次 feedback/rerun 时丢失")

    produced = (project / "output.html").read_text(encoding="utf-8")
    assert FROM_PAGE in produced, "生成出来的页面里没有页面自己的 section 文本"
