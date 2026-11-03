"""Shell acceptance (verify_portable 纪律 · 0.9.0 Tauri 壳).

静态半场：打包不变量 + Rust 侧关键决策与 Python 侧镜像一致。
运行半场（--run-e2e，需桌面环境）：真跑壳 exe + sidecar，探测 /api/health。

    python scripts/verify_shell.py            # 静态验收（CI/本地均可）
    python scripts/verify_shell.py --run-e2e  # 本地 GUI 冒烟（会弹窗）
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "src-tauri"

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def rust_source() -> str:
    return (SIDECAR / "src" / "main.rs").read_text(encoding="utf-8")


def static_checks() -> None:
    conf = (SIDECAR / "tauri.conf.json").read_text(encoding="utf-8")
    check("conf: frontendDist=loader", '"./loader"' in conf)
    check("conf: nsis target", '"nsis"' in conf)
    check("conf: identifier", '"com.kratoslee.htmlninefox"' in conf)
    for icon in ("icons/icon.png", "icons/icon.ico"):
        check(f"icon: {icon}", (SIDECAR / icon).is_file())
    check("loader page", (SIDECAR / "loader" / "index.html").is_file())

    rust = rust_source()
    # Python 镜像 Rust 的 sidecar 定位链（文档契约：HTMLNINEFOX_SIDECAR >
    # exe 邻位 > sidecar/ > build 产物），任何一侧漂移都算失败。
    check("rust: strict-port passed", '"--strict-port"' in rust)
    check("rust: no-browser passed", '"--no-browser"' in rust)
    check("rust: health poll", "/api/health" in rust)
    check("rust: kill on exit", "kill" in rust and "exit" in rust)
    check("rust: env override", "HTMLNINEFOX_SIDECAR" in rust)
    check("rust: build onedir candidate",
          '"windows"' in rust and '"HtmlNineFox.exe"' in rust and "build" in rust)

    # 版本一致性：壳版本与 pyproject 主版本同主号（0.9.x 对齐）
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    app_version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    shell_version = re.search(r'"version": "([^"]+)"', conf).group(1)
    check("version: same minor line",
          shell_version.split(".")[:2] == app_version.split(".")[:2],
          f"shell={shell_version} app={app_version}")

    bundle_script = ROOT / "packaging" / "shell" / "build_shell_bundle.py"
    check("bundle script exists", bundle_script.is_file())


def run_e2e() -> None:
    """GUI 冒烟：直接拉 sidecar exe 到空闲端口 → 探活 → 再手动跑壳 exe。
    壳本身开窗，故只适合本地桌面环境；CI 不跑这一段。"""
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    exe = next((p for p in [
        ROOT / "src-tauri" / "sidecar" / "HtmlNineFox" / "HtmlNineFox.exe",
        ROOT / "build" / "windows" / "dist" / "HtmlNineFox" / "HtmlNineFox.exe",
    ] if p.is_file()), None)
    if exe is None:
        check("e2e: sidecar exe", False, "先跑 build_shell_bundle.py 或 build_portable.py")
        return
    process = subprocess.Popen(
        [str(exe), "--port", str(port), "--strict-port", "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 45
        healthy = False
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/health", timeout=3) as response:
                    if response.status == 200:
                        healthy = True
                        break
            except Exception:
                time.sleep(0.5)
        check(f"e2e: /api/health 200 on :{port}", healthy)
    finally:
        process.terminate()
        process.wait(timeout=15)
    print("NOTE: 壳窗口全链路（双击→托盘→关窗回收）请按发布前人工清单走一遍")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-e2e", action="store_true")
    args = parser.parse_args()
    static_checks()
    if args.run_e2e:
        run_e2e()
    print(f"\n{'ALL GREEN' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
