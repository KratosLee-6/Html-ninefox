"""验证「打包产物里真的有 static/ 的每一个文件」，而不是「构建 job 变绿」。

这份脚本要堵的洞
----------------
`htmlninefox/server/static/` 是工作台的全部前端资源，而它进包靠的是
`pyproject.toml` 里**手写的** `[tool.setuptools.package-data]` 白名单。v0.6.3 本周
往 `static/` 加了 `fox-core.js`（从 index.html 抽离出来的前端内核），`.js` 恰好在
白名单里所以没出事——但「恰好」不是保证：白名单是正则式的，下一个新文件格式
（`.webmanifest`、`.json`、`.woff2`、子目录）随时可能匹配不上，而匹配不上的后果
是**用户下载到的包前端全废，所有门禁全绿**。

更隐蔽的是第二种失效：白名单匹配到了文件，但 `htmlninefox/server/app.py` 的
`STATIC_FILES` 没登记，于是路由 404，工作台同样全废——而这一条与 package-data
**完全独立**，两件事都得查。`STATIC_FILES` 是手写字典，漏登记没有任何测试会红
（服务器测试用的是仓库里的源码树，不是构建产物）。

做法
----
真的把 wheel 打出来（`setuptools.build_meta.build_wheel`，和 pip 走的是同一个
PEP 517 钩子），真的把 zip 打开，逐个文件比对**清单与字节**。不扫描
`pyproject.toml` 文本然后 grep pattern——那验证的是文本形状，一行注释就能满足。

在仓库里就地构建是被刻意避开的：setuptools 的 `build/lib` 是增量目录，上一次
构建留下的副本会被这一次原样打进 wheel，于是「从白名单里删掉一个 pattern」这种
变异在脏工作区里**可能测不出红**。因此每次构建都在系统临时目录里用一份干净的
源码快照进行。

用法
----
    python scripts/verify_package_payload.py            # 人工/CI 可读的完整报告
    python scripts/verify_package_payload.py --build-wheel <目录>
    python scripts/verify_package_payload.py --mutate    # 变异验证（N/N CAUGHT）

`tests/test_package_payload.py` 是门禁本身；本脚本只负责**产出那个产物**。
两者各自独立比对一遍 zip，是有意为之：门禁不采信脚本的结论，脚本也不采信门禁的
结论，单点判断被破坏时不会两边一起变绿。
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "htmlninefox" / "server" / "static"
INDEX_HTML = STATIC_DIR / "index.html"
APP_PY = ROOT / "htmlninefox" / "server" / "app.py"  # 变异目标之一
PYPROJECT = ROOT / "pyproject.toml"  # 变异目标之一，也是 build 的必需输入
GATE = "tests/test_package_payload.py"

# wheel 内部的路径前缀。包名是 htmlninefox，static 目录不是包（没有 __init__.py），
# 因此它在 wheel 里挂在 htmlninefox/server/static/ 下。
WHEEL_STATIC_PREFIX = "htmlninefox/server/static/"

# 构建所需的顶层输入。新增构建输入时必须补进来，否则「构建的是另一份源码」这种
# 假绿就回来了——pyproject 的 readme/license 指向的文件缺失时 setuptools 会报错，
# 但 MANIFEST.in 之类不参与报错。
BUILD_INPUT_FILES = (
    "pyproject.toml", "setup.py", "setup.cfg", "MANIFEST.in",
    "README.md", "README.rst", "LICENSE", "LICENSE.txt",
)
BUILD_INPUT_DIRS = ("htmlninefox",)

# index.html 里的外部脚本引用。只认根相对路径；协议相对与 http(s) 外链不是本包
# 负责的资源。
SCRIPT_SRC = re.compile(r"""<script[^>]*\ssrc\s*=\s*["']([^"']+)["']""", re.I)


def _reconfigure_streams() -> None:
    """Windows 控制台是 GBK/cp1252，直接打中文会在第一行就 UnicodeEncodeError。

    本地能打出来不代表 CI 能——这条正是把验证接进流水线之后才暴露的。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if (stream.encoding or "").lower().replace("-", "") not in ("utf8", "cp936", "gbk"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


@contextlib.contextmanager
def _chdir(target: Path):
    """`contextlib.chdir` 是 3.11+，本项目 requires-python 是 >=3.10。"""
    previous = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(previous)


def stage_sources(dest: Path) -> Path:
    """把构建所需的源码复制到 dest，返回 dest。

    为什么复制而不是就地构建：setuptools 的 `build/lib` 是**增量**目录。上一次构建
    复制进去的副本不会在这一次被清掉，于是「从 package-data 里删掉一个 pattern」
    的变异在脏工作区里会打出**仍然带着旧文件**的 wheel——门禁于是假绿，而且绿得
    很像真的。干净快照是唯一能可靠证伪的方式。
    """
    dest.mkdir(parents=True, exist_ok=True)
    for name in BUILD_INPUT_FILES:
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, dest / name)
    if not (dest / "pyproject.toml").is_file():
        raise SystemExit(f"{PYPROJECT} 不存在，无法构建")
    for name in BUILD_INPUT_DIRS:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, dest / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def build_wheel(out_dir: Path) -> tuple[Path, float]:
    """真正调 PEP 517 后端打一个 wheel。返回 (wheel 路径, 耗时秒)。

    走的是 `setuptools.build_meta.build_wheel`——和 `pip wheel .` / `python -m build`
    调用的是同一个后端钩子，不联网、不做隔离环境，所以 CI 上无需额外依赖。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="fox-payload-src-"))
    started = time.perf_counter()
    try:
        stage_sources(staging)
        from setuptools import build_meta

        with _chdir(staging), contextlib.redirect_stdout(sys.stderr):
            # setuptools 会往 stdout 刷几百行 copying/adding；本脚本把 stdout 当
            # 机器可读通道（`--build-wheel` 的 WHEEL= 行），构建噪音改走 stderr。
            name = build_meta.build_wheel(str(out_dir))
        elapsed = time.perf_counter() - started
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return out_dir / name, elapsed


def source_static_files() -> list[str]:
    """static/ 下真实存在的文件，路径相对 static/，递归。

    递归是有意的：白名单是平铺的 `server/static/*.js` 这类 pattern，一旦有人加了
    子目录（比如字体、图标集），平铺 pattern 不会递归覆盖，而这正是要抓的形状。
    """
    files = []
    for path in STATIC_DIR.rglob("*"):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        files.append(path.relative_to(STATIC_DIR).as_posix())
    return sorted(files)


def read_wheel_static(wheel: Path) -> dict[str, bytes]:
    """把 wheel 里 server/static/ 下的条目读成 {相对路径: 字节}。"""
    with zipfile.ZipFile(wheel) as zf:
        out: dict[str, bytes] = {}
        for name in zf.namelist():
            if name.startswith(WHEEL_STATIC_PREFIX) and not name.endswith("/"):
                out[name[len(WHEEL_STATIC_PREFIX):]] = zf.read(name)
        return out


def script_srcs() -> list[str]:
    """index.html 里每一个根相对的 <script src>。"""
    page = INDEX_HTML.read_text(encoding="utf-8")
    found = []
    for src in SCRIPT_SRC.findall(page):
        if not src.startswith("/") or src.startswith("//"):
            continue
        found.append(src)
    return sorted(set(found))


def check(wheel: Path) -> tuple[list[str], list[str]]:
    """返回 (问题列表, 统计行)。问题非空即门禁应红。"""
    problems: list[str] = []
    wanted = source_static_files()
    if not wanted:
        problems.append(f"{STATIC_DIR} 下一个文件都没有——门禁失去意义")
    shipped = read_wheel_static(wheel)

    missing = [name for name in wanted if name not in shipped]
    for name in missing:
        problems.append(f"static/{name} 存在于仓库但没进 wheel（package-data 白名单漏了）")
    changed = [name for name in wanted
               if name in shipped and shipped[name] != (STATIC_DIR / name).read_bytes()]
    for name in changed:
        problems.append(
            f"static/{name} 在 wheel 里的字节与仓库不一致（{len(shipped[name])} vs "
            f"{(STATIC_DIR / name).stat().st_size}）——产物很可能是陈旧的")

    # STATIC_FILES 必须作为运行时对象读，而不是把 app.py 当文本 grep。
    sys.path.insert(0, str(ROOT))
    from htmlninefox.server import app as server_app  # noqa: PLC0415 - 延迟导入

    srcs = script_srcs()
    if not srcs:
        problems.append("index.html 没有引用任何外部脚本——门禁失去意义")
    for src in srcs:
        filename = src.rsplit("/", 1)[-1]
        if not (STATIC_DIR / filename).is_file():
            problems.append(f"{src} 在 index.html 里被引用，但 static/{filename} 不存在")
            continue
        entry = server_app.STATIC_FILES.get(src)
        if entry is None:
            problems.append(f"{src} 没有登记进 app.py 的 STATIC_FILES —— 线上必然 404")
        elif entry[0] != filename:
            problems.append(f"{src} 在 STATIC_FILES 里指向 {entry[0]}，与页面请求的不符")
        if filename not in shipped:
            problems.append(f"{src} 没有进 wheel（package-data 白名单漏了）")
        elif shipped[filename] != (STATIC_DIR / filename).read_bytes():
            problems.append(f"{src} 在 wheel 里的字节与仓库不一致")

    stats = [
        f"wheel            {wheel.name}（{wheel.stat().st_size/1024:.0f} KB）",
        f"static 源文件     {len(wanted)} 个",
        f"wheel 内 static  {len(shipped)} 个",
        f"缺失             {len(missing)} 个 {'、'.join(missing) if missing else '—'}",
        f"字节不一致        {len(changed)} 个 {'、'.join(changed) if changed else '—'}",
        f"index.html 脚本   {len(srcs)} 个",
    ]
    return problems, stats


# --------------------------------------------------------------------- 变异验证

class MutationFailure(RuntimeError):
    """变异没有真的改到文件——硬失败，绝不记 MISSED。"""


def _swap(path: Path, new: bytes) -> None:
    path.write_bytes(new)


# 每个变异体返回 (说明, {要写入的文件: 新字节})。新字节为 None 表示「删掉这个文件」。
Mutation = tuple[str, dict[Path, bytes | None]]


def _mut_drop_js_pattern(root: Path) -> Mutation:
    """从 package-data 里删掉 `server/static/*.js` 这一条 pattern。

    这就是 v0.6.3 加 fox-core.js 时踩在边缘上的那一步：`.js` 恰好在白名单里所以没
    出事。删掉它，static/ 里的 11 个 js 全部进不了包。
    """
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    old = '"server/static/*.js", '
    if text.count(old) != 1:
        raise MutationFailure(f"pyproject.toml 里 `server/static/*.js` 出现次数是 "
                              f"{text.count(old)}，不是 1")
    new = text.replace(old, "", 1)
    return ("P1 删掉 package-data 的 server/static/*.js",
            {root / "pyproject.toml": new.encode("utf-8")})


def _mut_narrow_svg_pattern(root: Path) -> Mutation:
    """把 `*.svg` 改窄成一个具体文件名：白名单条目还在，文件却漏了两个。

    覆盖的是「手写正则白名单被悄悄改窄」这一类——条目数量没变，grep 文本也照样
    找得到 `server/static`，只有真产物里少了 logo-mark.svg 与 logo-horizontal.svg。
    """
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    old = '"server/static/*.svg"'
    if text.count(old) != 1:
        raise MutationFailure(f"pyproject.toml 里 `server/static/*.svg` 出现次数是 "
                              f"{text.count(old)}，不是 1")
    new = text.replace(old, '"server/static/icon.svg"', 1)
    return ("P2 把 server/static/*.svg 改窄成 icon.svg",
            {root / "pyproject.toml": new.encode("utf-8")})


def _mut_drop_whitelist_entry(root: Path) -> Mutation:
    """STATIC_FILES 漏登记一个真实存在、且被 index.html 引用的静态文件。

    产物里文件是在的、字节也对，只有服务端发不出去——工作台在浏览器里是一张白页，
    而构建 job 与全部测试都是绿的。
    """
    text = (root / "htmlninefox" / "server" / "app.py").read_text(encoding="utf-8")
    for line in text.splitlines(keepends=True):
        if '"/fox-core.js"' in line:
            return ("P3 app.py 的 STATIC_FILES 漏登记 /fox-core.js",
                    {root / "htmlninefox" / "server" / "app.py":
                     text.replace(line, "", 1).encode("utf-8")})
    raise MutationFailure("app.py 里找不到 /fox-core.js 的白名单条目")


# 打包期静默丢弃 / 替换内容的钩子。通过真实的 setuptools 构建路径生效：先正常
# 复制，再在 build_py 结束前动 build/lib 里的副本。这不是文本技巧，是一次真的
# 构建，真的少一个文件。
_DROP_HOOK = '''# 变异用：构建期静默丢弃一个静态文件（模拟打包管线漏掉一个资源）
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class _DropStaticFile(_build_py):
    def run(self):
        super().run()
        import os
        victim = os.path.join(self.build_lib, "htmlninefox", "server", "static",
                              "workbench-features.js")
        if os.path.isfile(victim):
            os.remove(victim)


setup(cmdclass={"build_py": _DropStaticFile})
'''

_STALE_HOOK = '''# 变异用：构建期把一个静态文件换成陈旧内容（清单对得上、字节不对）
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class _StaleStaticFile(_build_py):
    def run(self):
        super().run()
        import os
        victim = os.path.join(self.build_lib, "htmlninefox", "server", "static",
                              "index.html")
        if os.path.isfile(victim):
            with open(victim, "w", encoding="utf-8") as handle:
                handle.write("<!doctype html><html><body>stale</body></html>")


setup(cmdclass={"build_py": _StaleStaticFile})
'''


def _mut_silent_drop(root: Path) -> Mutation:
    hook = root / "setup.py"
    if hook.exists():
        raise MutationFailure("仓库里已经存在 setup.py，变异不能覆盖它")
    return ("P4 打包期静默丢弃 static/workbench-features.js",
            {hook: _DROP_HOOK.encode("utf-8")})


def _mut_stale_bytes(root: Path) -> Mutation:
    hook = root / "setup.py"
    if hook.exists():
        raise MutationFailure("仓库里已经存在 setup.py，变异不能覆盖它")
    return ("P5 打包期把 static/index.html 换成陈旧内容",
            {hook: _STALE_HOOK.encode("utf-8")})


MUTATIONS = (_mut_drop_js_pattern, _mut_narrow_svg_pattern, _mut_drop_whitelist_entry,
             _mut_silent_drop, _mut_stale_bytes)


def _run_gate() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", GATE, "-q", "-p", "no:cacheprovider",
         "--no-header", "--tb=no", "-rf"],
        cwd=ROOT, capture_output=True, text=True, timeout=1200,
        # 门禁输出中文；Windows 控制台是 GBK，不显式给 encoding 会让 proc.stdout
        # 变成 None，看起来像静默通过。
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def _failed_tests(proc: subprocess.CompletedProcess) -> list[str]:
    return [line.split(" ", 1)[-1].strip()
            for line in proc.stdout.splitlines()
            if line.startswith("FAILED ")]


def run_mutations() -> int:
    print("=" * 74)
    print("打包载荷门禁 · 变异验证")
    print("=" * 74)
    baseline = _run_gate()
    if baseline.returncode != 0:
        print("基线就红，无法做变异验证：")
        print(baseline.stdout[-3000:])
        return 2
    print(f"基线：{GATE} 全过\n")

    rows: list[tuple[str, str]] = []
    for make in MUTATIONS:
        try:
            label, edits = make(ROOT)
        except MutationFailure as exc:
            # 替换串没匹配上 = 什么都没测，记成 MISSED 会凭空造出假结论。
            print(f"HARD FAIL  {make.__name__}\n          {exc}")
            rows.append((make.__name__, "HARD FAIL"))
            continue

        # 按字节备份再写入。还原走备份字节，绝不用 git checkout --：本仓库里有用户
        # 未提交的改动，git 还原会把它们一起抹掉。
        original: dict[Path, bytes | None] = {}
        for path in edits:
            original[path] = path.read_bytes() if path.exists() else None
        if all(original[p] == edits.get(p) for p in edits):
            print(f"HARD FAIL  {label}\n          变异没有改变任何内容")
            rows.append((label, "HARD FAIL"))
            continue

        for path, new_bytes in edits.items():
            if new_bytes is None:
                path.unlink()
            else:
                _swap(path, new_bytes)
        try:
            proc = _run_gate()
        finally:
            for path, saved in original.items():
                if saved is None:
                    if path.exists():
                        path.unlink()
                else:
                    _swap(path, saved)

        verdict = "CAUGHT" if proc.returncode != 0 else "MISSED"
        rows.append((label, verdict))
        caught_by = ", ".join(t.rsplit("::", 1)[-1] for t in _failed_tests(proc)) or "-"
        print(f"{verdict:9} {label}\n          被抓于：{caught_by}")

    print("=" * 74)
    caught = sum(1 for _, v in rows if v == "CAUGHT")
    missed = [n for n, v in rows if v == "MISSED"]
    hard = [n for n, v in rows if v == "HARD FAIL"]
    print(f"{caught}/{len(rows)} CAUGHT")
    if missed:
        print("门禁在真实破坏下仍然全绿——视为无效门禁：")
        for name in missed:
            print(f"  MISSED   {name}")
    if hard:
        print("变异没有生效，本轮结论无效：")
        for name in hard:
            print(f"  HARD     {name}")
    print("=" * 74)
    return 1 if (missed or hard) else 0


# ------------------------------------------------------------------------- CLI

def _cmd_build_wheel(out: Path) -> int:
    wheel, elapsed = build_wheel(out)
    (out / ".built-wheel-name.txt").write_text(wheel.name, encoding="utf-8", newline="")
    print(f"WHEEL={wheel.name}")
    print(f"BUILD_SECONDS={elapsed:.2f}")
    return 0


def _cmd_verify() -> int:
    out = Path(tempfile.mkdtemp(prefix="fox-payload-whl-"))
    try:
        wheel, elapsed = build_wheel(out)
        print(f"构建耗时：{elapsed:.1f}s")
        problems, stats = check(wheel)
        for line in stats:
            print(f"  {line}")
        if problems:
            print(f"\n{len(problems)} 项问题：")
            for line in problems:
                print(f"  ! {line}")
            return 1
        print("\n打包载荷验证通过：static/ 的每一个文件都在 wheel 里且字节一致；"
              "index.html 请求的每一个脚本都存在、已登记、已打包。")
        return 0
    finally:
        shutil.rmtree(out, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    _reconfigure_streams()
    parser = argparse.ArgumentParser(description="验证 static/ 的真实打包载荷")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--mutate", action="store_true", help="跑变异验证")
    group.add_argument("--build-wheel", metavar="DIR",
                       help="只构建一个 wheel 并把文件名打到 stdout")
    args = parser.parse_args(argv)
    if args.mutate:
        return run_mutations()
    if args.build_wheel:
        return _cmd_build_wheel(Path(args.build_wheel))
    return _cmd_verify()


if __name__ == "__main__":
    raise SystemExit(main())
