"""Download a published release and check the bytes, not the metadata.

Why this exists
---------------
For three releases in a row the two 103MB Linux archives timed out on this
machine, so "the release was verified" actually meant "the digest file matched
the name of the asset". Nothing had been downloaded. That is the same shape as
v0.6.0 — four green build jobs and a package that crashed on start — and it is
the shape a metadata check cannot catch.

What it does, in order of how badly it would embarrass us:

  1. fetch the asset and its published digest
  2. re-hash what actually arrived and compare — a truncated download is caught
     here rather than after the user tries to run it
  3. open the archive and confirm it is not truncated or corrupt
  4. for the portable archive, confirm the front-end payload is really inside
  5. optionally boot the Windows portable and hit its health endpoint

Resumable
---------
The large archives are exactly the ones that kept timing out, so the download is
chunked and resumed: a failed attempt continues with a Range request instead of
starting over. That is the difference between "we gave up" and "we never actually
tried properly".

    python scripts/verify_release_assets.py v0.6.3
    python scripts/verify_release_assets.py v0.6.3 --asset "*.whl"
    python scripts/verify_release_assets.py v0.6.3 --boot-windows
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CHUNK = 1 << 20          # 1 MiB read window
RETRIES = 6
DEFAULT_GLOB = "*.zip"


def gh(*args: str) -> str:
    out = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} 失败：{out.stderr.strip()[:300]}")
    return out.stdout


def token() -> str:
    return subprocess.run(["gh", "auth", "token"], capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout.strip()


def digest_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _release_payload(tag: str, repo: str = "KratosLee-6/Html-ninefox") -> dict:
    """The release for this tag, draft or not.

    `releases/tags/<tag>` returns 404 for a draft — the API will not resolve a
    tag that has no ref yet, and a draft has no ref until it is published. Since
    the whole point of running this against a draft is to check the upload
    before anyone can see it, "404 for a draft" is a detail of the design, not a
    reason to skip. Fall back to listing and matching on tag_name.
    """
    api = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    tok = token()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                api, headers={"Authorization": f"Bearer {tok}",
                              "Accept": "application/vnd.github+json"}),
                timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    listed = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases?per_page=100",
        headers={"Authorization": f"Bearer {tok}",
                 "Accept": "application/vnd.github+json"}), timeout=60).read())
    for r in listed:
        if r.get("tag_name") == tag:
            return r
    raise RuntimeError(f"仓库 {repo} 里没有 tag 为 {tag} 的发布（正式或草稿）")


def asset_url(repo: str, tag: str, name: str) -> tuple[str, int]:
    for a in _release_payload(tag, repo)["assets"]:
        if a["name"] == name:
            return a["url"], a["size"]
    raise RuntimeError(f"发布 {tag} 里没有附件 {name}")


def download(repo: str, tag: str, name: str, dest: Path) -> Path:
    """Fetch with Range-based resume. Returns the local path.

    If dest is already the right size it is left alone. The first version always
    started a fresh .part next to it, which meant re-downloading 100MB that was
    already sitting on disk — the exact cost this script exists to avoid.
    """
    url, size = asset_url(repo, tag, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and (not size or dest.stat().st_size == size):
        print(f"   跳过下载：{dest.name} 已在本地且大小相符", flush=True)
        return dest
    tok = token()
    for attempt in range(1, RETRIES + 1):
        have = part.stat().st_size if part.exists() else 0
        if size and have == size:
            break
        headers = {"Authorization": f"Bearer {tok}",
                   "Accept": "application/octet-stream"}
        if have:
            headers["Range"] = f"bytes={have}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                mode = "ab" if (have and r.status == 206) else "wb"
                last_report = 0.0
                with part.open(mode) as fh:
                    while True:
                        block = r.read(CHUNK)
                        if not block:
                            break
                        fh.write(block)
                        got_now = part.stat().st_size
                        # Report progress. A 100MB download with no output reads
                        # as a hung job; with it, a stall is distinguishable from
                        # a slow link at a glance.
                        if size and got_now - last_report > 10 * 1024 * 1024:
                            last_report = got_now
                            print(f"    {got_now / 1e6:.0f}/{size / 1e6:.0f} MB",
                                  flush=True)
        except Exception as exc:  # noqa: BLE001 - the point is to keep going
            now = part.stat().st_size if part.exists() else 0
            print(f"    第 {attempt}/{RETRIES} 次中断于 {now / 1e6:.1f}MB"
                  f"（{type(exc).__name__}），续传", flush=True)
            time.sleep(min(30, 3 * attempt))
            continue
        now = part.stat().st_size
        if size and now >= size:
            break
    if part.exists() and (not size or part.stat().st_size == size):
        part.replace(dest)
        return dest
    raise RuntimeError(f"{name} 只下了 {part.stat().st_size if part.exists() else 0}"
                       f" / {size} 字节，判定为未完成")


def published_digest(repo: str, tag: str, name: str, into: Path) -> str | None:
    """The digest published alongside the asset, if any."""
    out: dict[str, str] = {}
    for a in _release_payload(tag, repo)["assets"]:
        if a["name"] in (name + ".sha256.txt", f"{name}.sha256"):
            blob = urllib.request.urlopen(urllib.request.Request(
                a["url"], headers={"Authorization": f"Bearer {token()}",
                                   "Accept": "application/octet-stream"}),
                timeout=60).read().decode("utf-8", "replace")
            m = re.search(r"\b([0-9a-fA-F]{64})\b", blob)
            if m:
                return m.group(1).lower()
    return None


def check_archive(path: Path) -> list[str]:
    problems: list[str] = []
    if path.suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                bad = z.testzip()
                if bad:
                    problems.append(f"归档里有损坏条目：{bad}")
                if not names:
                    problems.append("归档是空的")
        except zipfile.BadZipFile as exc:
            problems.append(f"不是有效的 zip：{exc}")
    elif path.name.endswith((".tar.gz", ".tgz")):
        import tarfile
        try:
            with tarfile.open(path) as t:
                if not t.getnames():
                    problems.append("归档是空的")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"不是有效的 tar.gz：{exc}")
    return problems


def check_static_payload(repo: str, tag: str, path: Path) -> list[str]:
    """Is the front-end actually inside this archive?

    A missing static file is the v0.6.0 shape: the archive is well formed, every
    digest matches, and the product is dead on arrival.

    Two package shapes exist and the difference decides the answer. The Windows
    portable and the macOS zip are frozen PyInstaller builds with the front end
    loose under _internal/.../server/static/. The Linux tarball ships a wheel
    plus its dependencies, so the same files sit one level deeper, inside
    htmlninefox-<version>-py3-none-any.whl.

    A check that only knows the first shape reports all 22 files missing on a
    perfectly good package. That is exactly what the first version of this
    function did, and it is why a negative result here gets cross-checked against
    the archive's real layout before it is believed.
    """
    problems: list[str] = []
    try:
        listing = gh("api", f"repos/{repo}/contents/htmlninefox/server/static?ref={tag}")
    except RuntimeError:
        return ["拿不到该 ref 的 static 清单"]
    want = {e["name"] for e in json.loads(listing) if e.get("type") == "file"}

    def _inside_wheel(data: bytes) -> set[str]:
        import io
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            # Note the missing leading slash: entries inside a wheel are
            # "htmlninefox/server/static/…", not "/htmlninefox/server/static/…".
            # Requiring the slash matches the frozen Windows build (which has
            # _internal/ in front) and silently matches nothing in a wheel.
            return {n.rsplit("/", 1)[-1] for n in z.namelist()
                    if "/server/static/" in n}

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            shipped = {n.rsplit("/", 1)[-1]
                       for n in z.namelist() if "/server/static/" in n}
    elif path.name.endswith((".tar.gz", ".tgz")):
        import tarfile
        shipped = set()
        with tarfile.open(path) as t:
            for n in t.getnames():
                if "/server/static/" in n:
                    shipped.add(n.rsplit("/", 1)[-1])
            if not shipped:
                for n in t.getnames():
                    base = n.rsplit("/", 1)[-1]
                    if base.startswith("htmlninefox-") and base.endswith(".whl"):
                        fh = t.extractfile(n)
                        if fh is not None:
                            shipped = _inside_wheel(fh.read())
                            print(f"   （前端在归档自带的 {base} 里）", flush=True)
                            break
    else:
        return problems

    if not shipped:
        return ["归档里找不到任何前端文件——装完就是白屏"]

    missing = sorted(want - shipped)
    if missing:
        problems.append(f"该版本 static/ 里的这些文件不在归档中：{missing}")
    return problems


def boot_windows_portable(archive: Path) -> list[str]:
    """Unpack the portable, start it, and ask it whether it is alive."""
    problems: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="fox-portable-"))
    try:
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
        root = next((p for p in tmp.iterdir() if p.is_dir()), None)
        if root is None:
            return ["便携包里没有顶层目录"]
        exe = next(root.glob("*.exe"), None)
        if exe is None:
            return ["便携包里没有 exe"]

        spec = importlib_util_load()
        proc = subprocess.Popen([str(exe)], cwd=str(root),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port, health = spec.probe_health(timeout=150.0, proc=proc)
        except SystemExit as exc:
            problems.append(f"启动后 150s 内没有提供服务：{exc}")
            return problems
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()

        if str(health.get("version")) != spec.expected_version():
            problems.append(f"健康检查报的版本是 {health.get('version')}，"
                            f"与仓库声明的 {spec.expected_version()} 不符")
        page = spec.fetch(port, "/").decode("utf-8", "replace")
        for marker in ("FoxActions", "export-format", "intakeFetchBatch"):
            if marker not in page:
                problems.append(f"工作台页面缺少 {marker}")
        scripts = {s.rsplit("/", 1)[-1] for s in
                   re.findall(r'<script[^>]*\ssrc="([^"]+)"', page)}
        for s in sorted(scripts):
            try:
                if not spec.fetch(port, "/" + s):
                    problems.append(f"/{s} 返回空")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"/{s} -> {type(exc).__name__}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


def importlib_util_load():
    """Load packaging/verify_portable.py by path; it is not an importable package."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fox_verify_portable", ROOT / "packaging" / "verify_portable.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--repo", default="KratosLee-6/Html-ninefox")
    ap.add_argument("--asset", action="append", default=None,
                    metavar="GLOB",
                    help="可重复。附件名或 glob；不传则默认 *.zip。"
                         "发布流水线用多个 --asset 覆盖 .exe/.zip/.tar.gz/.run/.whl")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--keep", action="store_true", help="保留下载的附件")
    ap.add_argument("--boot-windows", action="store_true",
                    help="额外把 Windows 便携包真的启动一次（只能在 Windows 上做）")
    args = ap.parse_args()

    # The release is looked up through _release_payload, which also finds drafts —
    # this is meant to run against a draft that nobody can see yet.
    patterns = args.asset or [DEFAULT_GLOB]
    assets = [a for a in _release_payload(args.tag, args.repo)["assets"]
              if any(fnmatch(a["name"], p) for p in patterns)]
    if not assets:
        print(f"没有附件匹配 {patterns}")
        return 2

    into = Path(args.dir) if args.dir else Path(
        tempfile.mkdtemp(prefix=f"fox-release-{args.tag}-"))
    into.mkdir(parents=True, exist_ok=True)
    print(f"发布 {args.tag}，待验 {len(assets)} 个附件，落地 {into}\n")

    failures: list[str] = []
    for a in assets:
        name = a["name"]
        if name.endswith(".sha256.txt") or name.endswith(".sha256"):
            continue
        size_mb = a["size"] / 1e6
        # flush everywhere: stdout is block-buffered when piped or captured by
        # CI, so without this a 100MB download looks like a hung job and you
        # cannot tell progress from a stall.
        print(f"── {name}  ({size_mb:.1f} MB)", flush=True)
        try:
            local = download(args.repo, args.tag, name, into / name)
        except RuntimeError as exc:
            print(f"   下载未完成：{exc}")
            failures.append(f"{name}: 下载未完成")
            continue

        problems: list[str] = []
        want = published_digest(args.repo, args.tag, name, into)
        got = digest_of(local)
        if want is None:
            problems.append("发布里没有对应的摘要文件——无法证明这包就是构建出来那个")
        elif want != got:
            problems.append(f"摘要不匹配：公布 {want}，实得 {got}")
        else:
            print(f"   OK  摘要一致 {got[:16]}…")

        problems += check_archive(local)
        problems += check_static_payload(args.repo, args.tag, local)

        if args.boot_windows and name.endswith(".zip") and "Windows" in name:
            print("   正在真实启动便携包……", flush=True)
            problems += boot_windows_portable(local)
            if not problems:
                print("   OK  启动成功并通过了健康检查与前端路由")

        if problems:
            for p in problems:
                print(f"   ✗  {p}")
            failures.append(f"{name}: " + "; ".join(problems))
        else:
            print("   OK  全部检查通过")

        if not args.keep:
            local.unlink(missing_ok=True)

    print()
    if failures:
        print(f"FAILED — {len(failures)} 个附件有问题：")
        for f in failures:
            print("  -", f)
        return 1
    print(f"全部通过：{len(assets)} 个附件的字节、归档完整性与前端载荷都核对无误")
    if not args.keep:
        shutil.rmtree(into, ignore_errors=True)
    return 0


def fnmatch(name: str, pattern: str) -> bool:
    import fnmatch as _f
    return _f.fnmatch(name, pattern) or _f.fnmatch(name, pattern + "*")


if __name__ == "__main__":
    raise SystemExit(main())
