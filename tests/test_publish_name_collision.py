"""Two runs in the same second must not fight over one project directory.

`WinError 5` on `staging.rename(target)` was a bare, unexplained failure: the
message names neither the collision nor a retry. Two things were wrong, both
measured rather than reasoned about:

* `_publish_project` passed the full `html9n-<ts>` back into
  `_next_project_name` as if it were a timestamp, producing a real directory
  named `html9n-html9n-2026-10-07-012829-2`.
* the obvious repair — splitting on the last `-` — is not an inverse of that
  construction, because the timestamp itself ends in digits. The "free" name
  came out `html9n-2026-10-07-12830`: a different timestamp, silently wrong.

And the underlying gap: `_next_project_name` checks existence and then names.
Two runs in the same second both receive `html9n-<ts>`. Serial runs are saved
by the retry at publish time; the rename is the only atomic claim on the final
name, so that is where the retry has to live.
"""

from __future__ import annotations

import pytest

from htmlninefox.pipeline import (
    _PUBLISH_ATTEMPTS,
    _free_project_name,
    _next_project_name,
    _publish_project,
)

TS = "2026-10-07-012829"
NAME = f"html9n-{TS}"


def staging(out, tag: str):
    d = out / f".gen-{tag}"
    d.mkdir()
    (d / f"{tag}.txt").write_text(tag, encoding="utf-8")
    return d


def test_two_same_second_runs_get_the_same_reserved_name(tmp_path):
    """The reservation is check-then-use, and this documents that fact.

    Neither call can be guaranteed free; publishing is what has to cope. If this
    ever starts failing, the reservation became atomic and the publish retry
    below is dead code worth revisiting.
    """
    assert _next_project_name(tmp_path, TS) == _next_project_name(tmp_path, TS) == NAME


def test_publishing_twice_yields_two_directories(tmp_path):
    first = _publish_project(tmp_path, NAME, staging(tmp_path, "a"))
    second = _publish_project(tmp_path, NAME, staging(tmp_path, "b"))
    assert first.name == NAME
    assert second.name == f"{NAME}-2"
    assert (first / "a.txt").exists()
    assert (second / "b.txt").exists()


def test_no_doubled_prefix_appears_in_any_published_name(tmp_path):
    """The regression: `html9n-html9n-...` is a real directory on disk."""
    _publish_project(tmp_path, NAME, staging(tmp_path, "a"))
    second = _publish_project(tmp_path, NAME, staging(tmp_path, "b"))
    assert not second.name.startswith("html9n-html9n")


def test_the_timestamp_survives_a_collision(tmp_path):
    """`-2` is appended to the whole name, never spliced into it.

    Splitting on the last `-` reads `...-01` + `2829` and yields
    `html9n-2026-10-07-12830` — a different timestamp that still looks valid.
    """
    _publish_project(tmp_path, NAME, staging(tmp_path, "a"))
    second = _publish_project(tmp_path, NAME, staging(tmp_path, "b"))
    assert second.name == f"{NAME}-2", f"timestamp mangled: {second.name}"
    assert second.name.startswith("html9n-2026-10-07-0128")


def test_free_name_keeps_counting_past_gaps(tmp_path):
    for suffix in ("", "-2", "-3"):
        (tmp_path / f"{NAME}{suffix}").mkdir()
    assert _free_project_name(tmp_path, NAME) == f"{NAME}-4"


def test_free_name_returns_the_name_when_it_is_free(tmp_path):
    assert _free_project_name(tmp_path, "html9n-never-used") == "html9n-never-used"


def test_publish_gives_up_with_a_message_that_names_the_problem(tmp_path, monkeypatch):
    """Exhausting the attempts must not surface as a bare WinError 5.

    The original failure was `PermissionError: [WinError 5] 拒绝访问` with no
    hint that a name collision was involved, which is why it cost a round of
    investigation to classify as transient.
    """
    path_cls = _publish_project.__globals__["Path"]
    real_rename = path_cls.rename
    attempts = {"n": 0}
    # Every candidate from -2 upwards is occupied, and the first is occupied
    # too, so no attempt can succeed and the loop must terminate by giving up.
    for suffix in ("", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9", "-10"):
        (tmp_path / f"{NAME}{suffix}").mkdir()

    def always_busy(self, target):
        attempts["n"] += 1
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(path_cls, "rename", always_busy)

    with pytest.raises(FileExistsError) as exc:
        _publish_project(tmp_path, NAME, staging(tmp_path, "a"))

    assert attempts["n"] == _PUBLISH_ATTEMPTS
    assert NAME in str(exc.value)