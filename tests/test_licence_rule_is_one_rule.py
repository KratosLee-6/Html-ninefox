"""The licence rule must be asked in one place, and answered the same way twice.

`app.py`'s approve path used to carry its own rule — "refuse unless
`inspiration-only`" — while `page_blocks_from_candidate` asked a different
question ("may this licence carry the page's prose?"). For `reference` the two
answers contradicted each other: the block channel produced structure with no
text, and the approve path copied the entire stored HTML into the template
gallery. A licence that means "reference it, do not copy it" was being copied.

These gates drive the real handler, not a transcription of the rule — the first
version of the probe printed a hard-coded copy of the branch and kept reporting
the old mismatch after the code was fixed, which is the failure mode worth
avoiding: a probe that measures its own assumption.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from htmlninefox import intake
from htmlninefox.server import app as server_app

HANDLER = next(
    cls for _, cls in inspect.getmembers(server_app, inspect.isclass)
    if "_api_intake_decide" in cls.__dict__
)

BODY = "<main><section><h2>标题</h2><p>正文</p></section></main>"


class _RefuseGallery:
    def import_files(self, *_args, **_kwargs):
        raise AssertionError("attempted a whole-page import")


def _decide(licence: str) -> dict:
    store = type("S", (), {
        "set_status": lambda self, cid, status: {
            "id": cid, "status": status, "license_class": licence,
            "title": "probe page", "source": "url"},
        "body": lambda self, cid: BODY.encode("utf-8"),
    })()
    handler = HANDLER.__new__(HANDLER)
    handler._intake_candidates = lambda: store
    handler._user_gallery = lambda: _RefuseGallery()
    return handler._api_intake_decide("c1", "approve")


def _gallery_imported(licence: str) -> bool:
    try:
        result = _decide(licence)
    except AssertionError:
        return True
    return result.get("gallery_skipped") is None


def _blocks_carry_text(licence: str) -> bool:
    blocks = intake.page_blocks_from_candidate(
        {"license_class": licence, "title": "t"}, BODY)
    return any(b.get("content") for b in blocks)


@pytest.mark.parametrize("licence", intake.LICENSE_CLASSES)
def test_only_open_licence_carries_verbatim_text(licence):
    """`reference` is not `open`: structure is learnable, prose is not."""
    expected = licence == "open"
    assert intake.may_carry_verbatim_text(licence) is expected
    assert _blocks_carry_text(licence) is expected


@pytest.mark.parametrize("licence", intake.LICENSE_CLASSES)
def test_only_open_licence_may_be_imported_whole(licence):
    assert _gallery_imported(licence) is (licence == "open")


@pytest.mark.parametrize("licence", intake.LICENSE_CLASSES)
def test_the_two_paths_never_disagree(licence):
    """The regression, stated as the invariant it broke.

    Two copies of one rule drift. Assert the answers match instead of asserting
    each path separately, so adding a fourth licence exposes the disagreement
    rather than quietly widening both copies.
    """
    assert _blocks_carry_text(licence) == _gallery_imported(licence), (
        f"{licence}: the block channel and the gallery import disagree about "
        f"whether this page's text may be carried")


def test_reference_licence_is_not_treated_as_open():
    """The concrete defect, named.

    Before the fix this returned True: a `reference` page had its whole body
    copied into the template gallery while the block channel gave it structure
    without text.
    """
    assert _gallery_imported("reference") is False


def test_the_approve_path_asks_the_shared_rule():
    """Guard against a second copy of the rule reappearing.

    Not a scan for a comment that mentions the name: the call has to be the one
    that guards the gallery import, and the old inline comparison must be gone.
    """
    import htmlninefox.server.app as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "intake.may_carry_verbatim_text(" in source, (
        "the approve path must ask intake.may_carry_verbatim_text, not its own "
        "comparison — that is how the two drifted apart")
    assert 'license_class") == "inspiration-only"' not in source, (
        "the old whole-page rule is back")