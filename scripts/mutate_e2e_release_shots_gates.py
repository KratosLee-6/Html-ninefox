"""反向验证：拆掉 e2e 发布截图的 opt-in 闸门，门禁必须变红。

对每一条修复分别回退一次，确认对应门禁真的会失败。门禁全绿但反向验证
抓不到，说明门禁在测「源码里有没有某个词」，而不是在测真实行为。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
E2E = REPO / "e2e_verify.py"
GATE = "tests/test_e2e_release_shots_are_opt_in.py"

def _insert_mkdir(src: str) -> str:
    anchor = 'OUT = HERE / "e2e-output"'
    return src.replace(anchor, 'RELEASE_SHOTS.mkdir(parents=True, exist_ok=True)\n' + anchor, 1)


def _unconditional_path(src: str) -> str:
    start = src.index("RELEASE_SHOTS = (")
    end = src.index(")", src.index("v{__version__}", start)) + 1
    return src[:start] + 'RELEASE_SHOTS = HERE / "assets" / "screenshots" / f"v{__version__}"' + src[end:]


def _drop_guard(src: str) -> str:
    guarded = (
        '            if _WRITE_RELEASE_SHOTS:\n'
        '                await page.screenshot(path=RELEASE_SHOTS / "workbench-overview.png")'
    )
    bare = '            await page.screenshot(path=RELEASE_SHOTS / "workbench-overview.png")'
    return src.replace(guarded, bare, 1)


# (名称, 构造「未修复」源码的函数, 必须变红的那条门禁)
#
# 这里刻意不写「修复前的原文片段」：修复已经落地，源码里根本不存在那些
# 文本，拿它们做 `old in original` 检查会永远判成 MISSING TARGET。
# 正确做法是**构造**未修复形态，并在下面断言它确实与原文不同。
REGRESSIONS = [
    (
        "恢复无条件 mkdir",
        _insert_mkdir,
        "test_default_run_does_not_create_any_release_screenshot_directory",
    ),
    (
        "路径重新无条件指向发布目录",
        _unconditional_path,
        "test_default_run_targets_a_directory_outside_the_release_tree",
    ),
    (
        "拿掉一处写入点的闸门",
        _drop_guard,
        "test_every_release_screenshot_write_is_behind_the_opt_in[workbench-overview.png]",
    ),
]


def run_gate(workdir: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", GATE, "-q", "-p", "no:cacheprovider", "--no-header"],
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def make_skeleton(dest: Path) -> None:
    """只铺门禁真正需要的东西。

    整个仓库有 17.8 万个文件 / 6.5 GB（大部分是工作区产物与截图），
    复制整棵树会让每条回退花掉几分钟，而且会把无关的体积带进临时目录。
    门禁只需要 e2e_verify.py、htmlninefox 包（为了 __version__）、
    门禁文件本身，以及一个已存在的 assets/screenshots/ 目录。
    """
    (dest / "tests").mkdir(parents=True)
    (dest / "assets" / "screenshots").mkdir(parents=True)
    shutil.copy2(REPO / "e2e_verify.py", dest / "e2e_verify.py")
    shutil.copy2(REPO / GATE, dest / "tests" / Path(GATE).name)
    shutil.copytree(
        REPO / "htmlninefox",
        dest / "htmlninefox",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for extra in ("pyproject.toml", "pytest.ini", "setup.cfg"):
        src = REPO / extra
        if src.exists():
            shutil.copy2(src, dest / extra)


def main() -> int:
    original = E2E.read_text(encoding="utf-8")
    results: list[tuple[str, bool, str]] = []

    for name, make_unfixed, target in REGRESSIONS:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            make_skeleton(work)
            target_file = work / "e2e_verify.py"
            unfixed = make_unfixed(original)
            if unfixed == original:
                print(f"SKIP  {name}: 回退构造没有实际改动源码（变异没生效）")
                results.append((name, False, "MUTATION DID NOT APPLY"))
                continue
            target_file.write_text(unfixed, encoding="utf-8", newline="")

            code, out = run_gate(work)
            caught = code != 0 and target.split("[")[0] in out
            results.append((name, caught, f"exit={code}"))
            print(f"{'CAUGHT' if caught else 'MISSED':>7}  {name}  (exit={code})")
            if not caught:
                print("        ---- gate output tail ----")
                print("\n".join(out.splitlines()[-15:]))

    missed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(missed)}/{len(results)} 回退全部被门禁抓到")
    return 1 if missed else 0


if __name__ == "__main__":
    # 每条回退都要复制一次骨架 + 跑一次 pytest，不加行缓冲时输出会被
    # 管道整个憋住，看起来像卡死。
    sys.stdout.reconfigure(line_buffering=True)
    raise SystemExit(main())
