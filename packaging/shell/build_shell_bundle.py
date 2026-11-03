"""Assemble the Tauri shell bundle: PyInstaller onedir -> sidecar/ -> NSIS.

0.9.0 收尾件。与 build_portable.py 分工：那个产便携包/安装包（浏览器形态），
这个把**同一份 onedir** 塞进 src-tauri/sidecar/ 供 Tauri 壳捆绑，再跑
`cargo tauri build` 出壳安装包（NSIS）。两种形态并存、互不替代。

    python packaging/shell/build_shell_bundle.py                 # 全流程
    python packaging/shell/build_shell_bundle.py --skip-portable  # 复用已有 onedir
    python packaging/shell/build_shell_bundle.py --check-only     # 只验不变量
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
SIDECAR_ROOT = ROOT / "src-tauri" / "sidecar"
APP_DIR = SIDECAR_ROOT / "HtmlNineFox"
PORTABLE_APP = ROOT / "build" / "windows" / "dist" / "HtmlNineFox"


def check_invariants() -> list[str]:
    """Packaging invariants the Rust side relies on (verify_portable 纪律的
    静态半场；运行半场见 verify_shell.py）。"""
    problems: list[str] = []
    conf = ROOT / "src-tauri" / "tauri.conf.json"
    text = conf.read_text(encoding="utf-8")
    if '"./loader"' not in text:
        problems.append("tauri.conf.json frontendDist 必须指向 ./loader")
    if "nsis" not in text:
        problems.append("tauri.conf.json bundle targets 必须含 nsis")
    for icon in ("src-tauri/icons/icon.png", "src-tauri/icons/icon.ico"):
        if not (ROOT / icon).is_file():
            problems.append(f"缺图标：{icon}")
    if not (ROOT / "src-tauri" / "loader" / "index.html").is_file():
        problems.append("缺加载页 src-tauri/loader/index.html")
    return problems


def stage_sidecar() -> Path:
    if not PORTABLE_APP.is_dir() or not (PORTABLE_APP / "HtmlNineFox.exe").is_file():
        raise FileNotFoundError(
            f"未找到 onedir：{PORTABLE_APP}——先跑 packaging/windows/build_portable.py "
            "或去掉 --skip-portable")
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)
    APP_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PORTABLE_APP, APP_DIR)
    print(f"staged: {APP_DIR}")
    return APP_DIR


def build_bundle() -> Path:
    command = ["cargo", "tauri", "build"]
    result = subprocess.run(command, cwd=ROOT / "src-tauri")
    if result.returncode != 0:
        raise SystemExit(f"cargo tauri build 失败（exit {result.returncode}）")
    bundles = ROOT / "src-tauri" / "target" / "release" / "bundle"
    installers = sorted(bundles.glob("nsis/*.exe"))
    if not installers:
        raise SystemExit(f"未找到 NSIS 产物：{bundles}")
    return installers[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-portable", action="store_true",
                        help="复用 build/windows/dist 里已有的 onedir")
    parser.add_argument("--check-only", action="store_true",
                        help="只验证打包不变量，不构建")
    args = parser.parse_args()

    problems = check_invariants()
    if problems:
        for problem in problems:
            print(f"INVARIANT FAIL: {problem}")
        return 1
    print("invariants ok")
    if args.check_only:
        return 0

    if not args.skip_portable:
        subprocess.run(
            [sys.executable, str(ROOT / "packaging" / "windows" / "build_portable.py")],
            cwd=ROOT, check=True)
    stage_sidecar()
    installer = build_bundle()
    print(f"shell-installer={installer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
