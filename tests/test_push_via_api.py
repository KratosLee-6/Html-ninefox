"""A push must publish the commit, not the working tree.

The incident this guards against is real and it was silent. `fox-api-push.py`
read each file with `(ROOT / path).read_bytes()`. With a dirty tree — that is,
whenever the next commit was already partly written — it published the NEXT
commit's `.github/workflows/test.yml` inside the PREVIOUS commit. Six other
files in the same push were correct, so nothing looked wrong; the next push
then refused with "ABORT: walked 40 commits without meeting the remote head
tree", a message about history that had nothing to do with history.

These gates drive the real `blob_bytes` and `upload_blob` against a throwaway
git repository whose working tree deliberately differs from the commit. They do
not read the source: a source scan would happily find the string
`git cat-file` in a comment and pass on code that still calls read_bytes.

The same shape covers the second half: an uploaded blob whose sha disagrees
with git's must raise, not be silently accepted — that is the check whose
absence let the wrong content reach the ref.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.push_via_api import BlobMismatch, blob_bytes, upload_blob

COMMITTED = b"THE COMMITTED CONTENT\n"
WORKTREE = b"THE UNCOMMITTED WORKING-TREE CONTENT\n"
SECOND_COMMIT = b"SECOND COMMIT CONTENT\n"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A repo with one committed file and a deliberately dirty working tree."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "gate@example.invalid")
    git(tmp_path, "config", "user.name", "gate")
    target = tmp_path / "ci.yml"
    target.write_bytes(COMMITTED)
    git(tmp_path, "add", "ci.yml")
    git(tmp_path, "commit", "-q", "-m", "first")
    # The second commit changes it again, and the tree is then dirtied with a
    # third state — exactly the shape in which read_bytes lies.
    target.write_bytes(SECOND_COMMIT)
    git(tmp_path, "commit", "-q", "-am", "second")
    target.write_bytes(WORKTREE)
    return tmp_path


def test_working_tree_really_is_dirty(repo: Path):
    """Guard the fixture itself.

    If the dirt did not take, every gate below would pass for the wrong
    reason — and a test that cannot fail is worse than no test.
    """
    assert (repo / "ci.yml").read_bytes() == WORKTREE


def test_blob_bytes_reads_the_commit_not_the_working_tree(repo: Path):
    first = git(repo, "rev-parse", "HEAD~1")
    assert blob_bytes(first, "ci.yml", root=repo) == COMMITTED


def test_blob_bytes_for_head_while_the_tree_is_dirtier(repo: Path):
    """Even for HEAD, the dirt must not leak in."""
    assert blob_bytes("HEAD", "ci.yml", root=repo) == SECOND_COMMIT


def test_blob_bytes_is_empty_for_a_path_missing_from_that_commit(repo: Path):
    assert blob_bytes("HEAD", "does-not-exist.txt", root=repo) == b""


def test_upload_blob_sends_the_committed_bytes(repo: Path):
    """The bytes handed to the API are the commit's, not the tree's."""
    sent: dict = {}
    first = git(repo, "rev-parse", "HEAD~1")

    def fake_call(method: str, path: str, tok: str, payload=None) -> dict:
        import base64
        sent["payload"] = payload
        sent["decoded"] = base64.b64decode(payload["content"])
        # A real API answers with the sha of what it stored, which is the sha
        # of the commit being pushed — not of HEAD.
        return {"sha": git(repo, "rev-parse", f"{first}:ci.yml")}

    sha = upload_blob("o/r", "tok", first, "ci.yml", call=fake_call, root=repo)

    assert sent["decoded"] == COMMITTED, "the API was handed the working tree"
    assert sha == git(repo, "rev-parse", f"{first}:ci.yml")


def test_upload_blob_raises_when_the_api_sha_disagrees(repo: Path):
    """A wrong sha must stop the push, not be adopted.

    The tree is built from whatever sha the API returned, so accepting a
    mismatch publishes the wrong content and moves the ref — with nothing but
    a green CI run to show for it.
    """
    def lying_call(method: str, path: str, tok: str, payload=None) -> dict:
        return {"sha": "0" * 40}

    first = git(repo, "rev-parse", "HEAD~1")
    with pytest.raises(BlobMismatch):
        upload_blob("o/r", "tok", first, "ci.yml", call=lying_call, root=repo)


def test_no_push_path_reads_files_from_disk(repo: Path):
    """`upload_blob` must not touch the filesystem for content.

    Deleting the file from disk changes nothing about what the commit holds, so
    a push that still succeeds is one that read from the commit. A push that
    needed the file would raise — which is the point.
    """
    first = git(repo, "rev-parse", "HEAD~1")
    (repo / "ci.yml").unlink()

    def fake_call(method: str, path: str, tok: str, payload=None) -> dict:
        return {"sha": git(repo, "rev-parse", f"{first}:ci.yml")}

    sha = upload_blob("o/r", "tok", first, "ci.yml", call=fake_call, root=repo)
    assert sha == git(repo, "rev-parse", f"{first}:ci.yml")