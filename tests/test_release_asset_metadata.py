"""Every published release must be checkable without downloading 100MB.

The gap this closes
-------------------
v0.6.1, v0.6.2 and v0.6.3 all shipped with release assets that had never been
downloaded on the machine that built them. "Verified" meant the digest file's
name matched the asset's name. That is the same blind spot as v0.6.0: every
build job green, and nothing had actually looked at what users would get.

Deep verification of a 100MB archive does not belong on every push, and it
should not be a thing a human has to remember. So this file covers the part that
is cheap and always true — the release is *checkable* — and
scripts/verify_release_assets.py covers the part that is expensive and
occasional.

Two halves, on purpose
----------------------
The checks are a pure function over a release description, so this file asks two
different questions and both are answered by running code:

  * "is the release as published checkable?" — the real GitHub API answers, for
    every release that exists
  * "would this checker notice if it were not?" — deliberately broken copies fed
    to the same function

The second half is the mutation check, done by construction. A separate
mutation script would have to stub the GitHub API and the digest downloads to
inject a bad release, and a stubbed API is itself a thing that can be wrong in a
way the test never sees. Feeding the pure function a broken dict has no such
second failure mode: the same code that reads the real release is the code being
tested against the broken one.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = "KratosLee-6/Html-ninefox"
ROOT = Path(__file__).resolve().parents[1]
RELEASES = ("v0.6.0", "v0.6.1", "v0.6.2", "v0.6.3")

# Installable payloads, as opposed to screenshots, videos and the digest files.
BINARY = re.compile(r"\.(exe|zip|tar\.gz|run|whl)$", re.I)
DIGEST_SUFFIXES = (".sha256.txt", ".sha256")
SHA256 = re.compile(r"\b([0-9a-fA-F]{64})\b")


def problems_with(release: dict, sidecars: dict[str, str]) -> list[str]:
    """Everything wrong with this release's asset metadata. Pure.

    `sidecars` maps an asset's digest-file name to the text published in it.
    """
    out: list[str] = []
    assets = release.get("assets", [])
    names = {a["name"] for a in assets}

    payloads = [a["name"] for a in assets if BINARY.search(a["name"])]

    for name in payloads:
        sidecar_name = next((name + s for s in DIGEST_SUFFIXES
                             if name + s in names), None)
        if sidecar_name is None:
            out.append(f"{name} 没有配套摘要——用户无法判断自己拿到的东西")
            continue
        body = sidecars.get(sidecar_name)
        if body is None:
            out.append(f"{name} 的摘要文件取不到内容")
        elif not SHA256.search(body):
            out.append(f"{name} 的摘要文件里没有 64 位十六进制摘要：{body[:60]!r}")

    version = str(release.get("tag_name", "")).lstrip("v")
    if version:
        stale = [n for n in payloads if version not in n]
        if stale:
            out.append(f"混进了名字不带本版本号的产物：{stale}——"
                       f"元数据看不出问题，用户下到的却是别的东西")

    if payloads:
        if release.get("draft"):
            out.append("带着可安装产物却仍是草稿——用户根本看不到它")
        if release.get("prerelease"):
            out.append("带着可安装产物却标成预发布。"
                       "v0.6.2 就是这样出去的：功能 100% 失败，"
                       "而它在发布页上看起来和正常版没有区别")
    return out


# --------------------------------------------------------------- real releases

def _fetch_release(tag: str) -> dict:
    proc = subprocess.run(
        ["gh", "api", f"repos/{REPO}/releases/tags/{tag}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        # Skipping here would be the exact shape this repository keeps removing:
        # a gate that quietly stops guarding the moment the environment is not
        # what it expected. In CI it fails and says what to set; on a machine
        # without `gh` credentials a skip is honest, because the author knows why.
        if os.environ.get("CI"):
            pytest.fail(
                "CI 里拿不到发布信息——这道门禁会静默失效。"
                "给这个 job 加上 GH_TOKEN: ${{ github.token }} 再跑。"
                f"（gh 原始错误：{proc.stderr.strip()[:160]}）")
        pytest.skip(f"拿不到 {tag} 的发布信息（gh 未登录或网络不通）："
                    f"{proc.stderr.strip()[:120]}")
    return json.loads(proc.stdout)


def _sidecars(release: dict) -> dict[str, str]:
    try:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, encoding="utf-8", check=True).stdout.strip()
    except subprocess.CalledProcessError:
        return {}
    out: dict[str, str] = {}
    for a in release.get("assets", []):
        if a["name"].endswith(DIGEST_SUFFIXES):
            try:
                with urllib.request.urlopen(urllib.request.Request(
                        a["url"], headers={"Authorization": f"Bearer {tok}",
                                           "Accept": "application/octet-stream"}),
                        timeout=60) as r:
                    out[a["name"]] = r.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - reported as a problem below
                out[a["name"]] = ""
    return out


@pytest.mark.parametrize("tag", RELEASES)
def test_published_releases_are_checkable(tag: str) -> None:
    """The real question: is what we published verifiable by a user?"""
    release = _fetch_release(tag)
    found = problems_with(release, _sidecars(release))
    assert not found, (
        f"{tag} 的发布元数据有问题：\n  " + "\n  ".join(found))


# ------------------------------------ can the checker see a broken release?

def _ok_release() -> dict:
    return {
        "tag_name": "v9.9.9",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": "HtmlNineFox-Windows-x64-9.9.9.zip"},
            {"name": "HtmlNineFox-Windows-x64-9.9.9.zip.sha256.txt"},
            {"name": "screenshot.png"},
        ],
    }


def _ok_sidecars() -> dict:
    return {"HtmlNineFox-Windows-x64-9.9.9.zip.sha256.txt": "a" * 64 + "  file\n"}


def test_a_well_formed_release_reports_nothing() -> None:
    assert problems_with(_ok_release(), _ok_sidecars()) == []


@pytest.mark.parametrize(
    "name, mutate_release, mutate_sidecars, expect",
    [
        ("附件没有配套摘要",
         lambda r: {**r, "assets": [r["assets"][0], r["assets"][2]]},
         lambda s: {}, "没有配套摘要"),
        ("摘要文件存在但内容不是摘要",
         lambda r: r,
         lambda s: {**s, "HtmlNineFox-Windows-x64-9.9.9.zip.sha256.txt": "CHECKSUM"},
         "没有 64 位十六进制摘要"),
        ("摘要文件压根没取到内容",
         lambda r: r,
         lambda s: {k: v for k, v in s.items() if "sha256" not in k},
         "取不到内容"),
        ("摘要文件是空的",
         lambda r: r,
         lambda s: {**s, "HtmlNineFox-Windows-x64-9.9.9.zip.sha256.txt": ""},
         "没有 64 位十六进制摘要"),
        ("混进别的版本的产物",
         lambda r: {**r, "assets": r["assets"] + [{"name": "HtmlNineFox-Windows-x64-9.9.8.zip"}]},
         lambda s: s, "不带本版本号"),
        ("可安装产物却标成草稿",
         lambda r: {**r, "draft": True},
         lambda s: s, "草稿"),
        ("可安装产物却标成预发布（v0.6.2 的形状）",
         lambda r: {**r, "prerelease": True},
         lambda s: s, "预发布"),
    ],
)
def test_the_checker_notices_each_way_a_release_can_be_unverifiable(
        name, mutate_release, mutate_sidecars, expect) -> None:
    """This is the mutation check: same code, deliberately broken release.

    "The gate passes" on its own proves only that today's releases happen to be
    fine. What matters is whether the checker can see a release that is not —
    and a checker that cannot is worse than none, because it looks like
    coverage.
    """
    found = problems_with(mutate_release(_ok_release()),
                          mutate_sidecars(_ok_sidecars()))
    assert any(expect in f for f in found), (
        f"这一条变异（{name}）没有被看见，problems_with 返回 {found}")


# ------------------------------------------- the draft-release lookup path

def test_the_release_lookup_falls_back_to_listing_for_a_draft() -> None:
    """`releases/tags/<tag>` returns 404 for a draft; the script must still find it.

    This is the path the whole draft-gated publish depends on. If it did not
    work, verify-release-assets would report "no assets match" against a draft
    that is full of them, and the gate would pass for the wrong reason — or fail
    every release and get switched off.

    It cannot be exercised against a real draft without creating one on a public
    repository, so the two HTTP answers it depends on are stubbed here instead:
    404 on the by-tag lookup, then a listing that contains the draft.
    """
    import importlib.util
    import urllib.error
    import urllib.request

    spec = importlib.util.spec_from_file_location(
        "fox_verify_release_assets", ROOT / "scripts" / "verify_release_assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    draft = {"tag_name": "v9.9.9", "draft": True, "assets": [
        {"name": "HtmlNineFox-Windows-x64-9.9.9.zip", "url": "u", "size": 1},
        {"name": "HtmlNineFox-Windows-x64-9.9.9.zip.sha256.txt", "url": "u", "size": 1},
    ]}
    other = {"tag_name": "v9.9.8", "draft": True, "assets": []}
    seen: list[str] = []

    class _Resp:
        def __init__(self, payload): self._payload = json.dumps(payload).encode()
        def read(self): return self._payload
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _NotFound(Exception):
        pass

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        seen.append(url)
        if "/releases/tags/" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return _Resp([other, draft])          # the listing, draft not first

    real_urlopen = urllib.request.urlopen
    real_token = mod.token
    mod.token = lambda: "stub"
    urllib.request.urlopen = fake_urlopen
    try:
        found = mod._release_payload("v9.9.9")
    finally:
        urllib.request.urlopen = real_urlopen
        mod.token = real_token

    assert any("/releases/tags/" in u for u in seen), "没有先试 by-tag 端点"
    assert any(u.endswith("/releases?per_page=100") for u in seen), \
        "404 之后没有回退到列举发布"
    assert found["draft"] is True and found["assets"], \
        f"回退没有找到那个草稿，返回了 {found}"


def test_the_release_lookup_raises_when_the_tag_is_gone_entirely() -> None:
    """If neither the tag nor the listing has it, that is an error, not an empty
    result. An empty result would read as "nothing to verify", which is exactly
    the kind of quiet pass this file exists to prevent."""
    import importlib.util
    import urllib.error
    import urllib.request

    spec = importlib.util.spec_from_file_location(
        "fox_verify_release_assets2", ROOT / "scripts" / "verify_release_assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class _Resp:
        def __init__(self, payload): self._payload = json.dumps(payload).encode()
        def read(self): return self._payload
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        if "/releases/tags/" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return _Resp([{"tag_name": "v0.0.1", "assets": []}])

    real_urlopen, real_token = urllib.request.urlopen, mod.token
    mod.token = lambda: "stub"
    urllib.request.urlopen = fake_urlopen
    try:
        with pytest.raises(RuntimeError, match="没有 tag 为"):
            mod._release_payload("v9.9.9")
    finally:
        urllib.request.urlopen, mod.token = real_urlopen, real_token
