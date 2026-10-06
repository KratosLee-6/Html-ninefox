"""Push one local commit to GitHub through the API.

`git push` is unusable from this machine: the transfer times out on the two
103MB release assets no matter how small the commit is, because the negotiation
walks the whole history. The git-data API needs only the objects this commit
actually adds, so it goes through in seconds.

Two safety rules, and the reason this is a script rather than a shell one-liner:

1. The local parent commit's tree MUST equal the remote head's tree before the
   ref is moved. If someone pushed from another machine in between, a push
   would silently drop their work, and the only symptom would be a green CI
   run on a repo that no longer matches what anyone tested.

2. Content is read from the COMMIT OBJECT, never from the working tree, and
   every uploaded blob's sha is checked against git's own. Reading the working
   tree once shipped the *next* commit's CI change inside the *previous*
   commit — a real incident, not a hypothetical.

    python push_via_api.py <repo> <commit> <remote-head-sha>
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "https://api.github.com"


def git(*args: str, root: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=root or ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          check=True).stdout.strip()


def blob_bytes(commit: str, path: str, root: Path | None = None) -> bytes:
    """The bytes of `path` as of `commit`.

    From the commit object, never from disk. `git cat-file blob` yields exactly
    the bytes git stored, already normalized per core.autocrlf, so there is
    nothing left to convert.

    Reading `(root / path).read_bytes()` instead is the bug this whole
    function exists to prevent: the working tree may already hold the next
    commit's edits, and pushing "this commit" would quietly publish them one
    commit early. The difference only shows up when the tree is dirty, which
    is exactly when nobody is looking.

    Returns `b""` when the path does not exist in that commit.
    """
    proc = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{path}"],
        cwd=root or ROOT, capture_output=True,
    )
    if proc.returncode != 0:
        return b""
    return proc.stdout


def upload_blob(repo: str, tok: str, commit: str, path: str,
                call=None, root: Path | None = None) -> str:
    """Upload one path as of `commit` and return the remote blob sha.

    Raises `BlobMismatch` when GitHub's sha differs from git's. Without that
    check the mismatch is silent: the tree is built from the sha GitHub
    returned, the ref moves, and the wrong content is published with a green
    run.
    """
    call = call or globals()["call"]
    raw = blob_bytes(commit, path, root)
    local_blob = git("rev-parse", f"{commit}:{path}", root=root)
    blob = call("POST", f"/repos/{repo}/git/blobs", tok, {
        "content": base64.b64encode(raw).decode(),
        "encoding": "base64"})
    if blob["sha"] != local_blob:
        raise BlobMismatch(
            f"{path}: git says {local_blob[:7]}, the API says {blob['sha'][:7]}")
    return blob["sha"]


class BlobMismatch(RuntimeError):
    """The uploaded blob is not the blob that commit names."""


def token() -> str:
    out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    return out.strip()


def call(method: str, path: str, tok: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    last: Exception | None = None
    for attempt in range(1, 5):
        req = urllib.request.Request(
            API + path, data=data, method=method,
            headers={"Authorization": f"Bearer {tok}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            # GitHub names the offending field; without printing it a 422 looks
            # like "something was rejected" and invites guessing.
            print(f"\nHTTP {e.code} on {method} {path}\n{detail[:1200]}")
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            # The proxy drops connections mid-transfer (SSL EOF is the common
            # one here). Retry rather than abandon a push that is mostly done.
            last = e
            print(f"  network error on {method} {path} (attempt {attempt}/4): {e}")
            time.sleep(2 * attempt)
    raise last  # type: ignore[misc]


def main() -> int:
    repo, tip, remote_head = sys.argv[1], sys.argv[2], sys.argv[3]
    tok = token()

    remote_head_tree = call("GET", f"/repos/{repo}/git/commits/{remote_head}",
                            tok)["tree"]["sha"]

    # Walk back from the tip until a commit's OWN tree equals the remote head's
    # tree. That commit is the base; everything after it still needs pushing.
    #
    # The check is on `cursor`, not on `cursor~1`. Comparing the parent's tree
    # and breaking out before appending `cursor` silently drops the last commit
    # in the chain — which is exactly what happened once: three commits went in,
    # two came out, and main was left referencing test files that were never
    # published.
    chain: list[str] = []
    cursor = tip
    while git("rev-parse", cursor + "^{tree}") != remote_head_tree:
        parent = git("rev-parse", f"{cursor}~1")
        if parent == cursor or len(chain) > 40:
            print("ABORT: walked 40 commits without meeting the remote head tree.")
            return 2
        chain.append(cursor)
        cursor = parent

    chain.reverse()  # oldest first
    print(f"base {cursor[:7]}  tree {remote_head_tree}  (matches remote head)")
    if not chain:
        print("nothing to push")
        return 0
    print(f"{len(chain)} commit(s) to push: "
          + " -> ".join(c[:7] for c in chain) + "\n")

    head = remote_head
    for commit in chain:
        parent = git("rev-parse", f"{commit}~1")
        changed = []
        for line in git("diff", "--name-status", parent, commit).splitlines():
            status, _, path = line.partition("\t")
            changed.append((status, path))

        entries = []
        for status, path in changed:
            try:
                sha = upload_blob(repo, tok, commit, path)
            except BlobMismatch as exc:
                print(f"  !! {exc}")
                return 3
            entries.append({"path": path, "mode": "100644", "type": "blob",
                            "sha": sha})
            print(f"  {status}  {path}  {sha[:7]}  "
                  f"{len(blob_bytes(commit, path))} bytes")

        tree = call("POST", f"/repos/{repo}/git/trees", tok,
                    {"base_tree": head and call(
                        "GET", f"/repos/{repo}/git/commits/{head}",
                        tok)["tree"]["sha"], "tree": entries})["sha"]
        head = call("POST", f"/repos/{repo}/git/commits", tok, {
            "message": git("log", "-1", "--format=%B", commit).strip(),
            "tree": tree, "parents": [head]})["sha"]
        print(f"  -> {commit[:7]} published as {head[:7]}\n")

    call("PATCH", f"/repos/{repo}/git/refs/heads/main", tok,
         {"sha": head, "force": False})
    print(f"pushed {tip[:7]} -> {head[:7]} on {repo} main")
    print(f"https://github.com/{repo}/commit/{head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())