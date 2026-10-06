"""跑一次 e2e 验收不应该改掉仓库里已发布版本的发布截图。

`assets/screenshots/v<version>/` 是**已发布**的发布物目录（README 与
RELEASE-NOTES 都直接引用里面的文件）。曾经 e2e_verify.py 在模块导入时
无条件 `mkdir` 它、并在每次运行时覆盖三张图，于是「跑一遍验收」会静默
改掉 git 工作区里那些已发布的图片。

这些门禁在**子进程里真的导入 e2e_verify**，读它算出来的 RELEASE_SHOTS，
而不是在源码里搜字符串 —— 后者挡不住「路径算对了但目录照样被建出来」。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# 在子进程里导入 e2e_verify，然后把关键常量吐出来。
PROBE = """
import json, os, sys
sys.path.insert(0, os.getcwd())
import e2e_verify as e
print("PROBE:" + json.dumps({
    "release_shots": str(e.RELEASE_SHOTS),
    "write_enabled": bool(e._WRITE_RELEASE_SHOTS),
    "dir_exists": e.RELEASE_SHOTS.is_dir(),
}))
"""


def probe_release_shots(env_extra: dict) -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(REPO)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"probe failed: {proc.stderr}"
    line = next(
        (l for l in proc.stdout.splitlines() if l.startswith("PROBE:")), None
    )
    assert line, f"no probe output: {proc.stdout!r} / {proc.stderr!r}"
    return json.loads(line[len("PROBE:") :])


def test_default_run_targets_a_directory_outside_the_release_tree():
    """默认（不开开关）时 RELEASE_SHOTS 绝不能指向 assets/screenshots/v*。"""
    info = probe_release_shots({})
    assert info["write_enabled"] is False
    release = Path(info["release_shots"])
    published = (REPO / "assets" / "screenshots").resolve()
    assert not release.resolve().is_relative_to(published), (
        f"默认仍然指向已发布截图目录: {release}"
    )


def test_default_run_does_not_create_any_release_screenshot_directory():
    """导入 e2e_verify 本身不得建出发布目录（曾经的 mkdir 在模块顶层）。"""
    shots_root = REPO / "assets" / "screenshots"
    before = {p.name for p in shots_root.iterdir() if p.is_dir()}
    info = probe_release_shots({})
    after = {p.name for p in shots_root.iterdir() if p.is_dir()}
    assert before == after, f"导入后新增了目录: {after - before}"
    assert info["dir_exists"] is False


def test_explicit_opt_in_retargets_the_release_directory():
    """显式开启时仍要指向 assets/screenshots/v<version>，不能被改坏。"""
    from htmlninefox import __version__

    info = probe_release_shots({"HTMLNINEFOX_E2E_RELEASE_SHOTS": "1"})
    assert info["write_enabled"] is True
    assert Path(info["release_shots"]) == REPO / "assets" / "screenshots" / f"v{__version__}"


@pytest.mark.parametrize(
    "filename", ["workbench-overview.png", "workbench-night.png", "export-center.png"]
)
def test_every_release_screenshot_write_is_behind_the_opt_in(filename):
    """三处发布截图写入必须逐个被 opt-in 闸门包住 —— 新增一处裸写要被抓到。

    闸门是**写入语句的上一行**（`if _WRITE_RELEASE_SHOTS:`），写入语句本身
    当然不以 if 开头。只看写入行会把正确的代码判成错的。
    """
    lines = (REPO / "e2e_verify.py").read_text(encoding="utf-8").splitlines()
    write_indexes = [
        i
        for i, line in enumerate(lines)
        if f'RELEASE_SHOTS / "{filename}"' in line and "page.screenshot" in line
    ]
    assert write_indexes, f"找不到 {filename} 的写入点（可能改名了？）"
    for i in write_indexes:
        guard = lines[i - 1].strip() if i else ""
        assert guard == "if _WRITE_RELEASE_SHOTS:", (
            f"{filename} 的写入没有被 opt-in 闸门保护（上一行是 {guard!r}）"
        )
