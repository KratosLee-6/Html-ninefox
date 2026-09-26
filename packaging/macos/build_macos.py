"""Build the macOS .app portable package (Apple Silicon).

Runs on macOS only (PyInstaller cannot cross-compile). Produces
release/HtmlNineFox-macOS-arm64-<version>.zip plus a SHA-256 checksum.
The archive keeps symlinks and executable bits via ditto.
"""

from __future__ import annotations

import hashlib
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"
BUILD = ROOT / "build" / "macos"
ENTRY = ROOT / "packaging" / "windows" / "launcher.py"
ICON_SOURCE = ROOT / "packaging" / "windows" / "htmlninefox.ico"

ICNS_SIZES = (16, 32, 64, 128, 256, 512, 1024)


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("version missing from pyproject.toml")
    return match.group(1)


def require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("build_macos.py must run on macOS (PyInstaller cannot cross-compile)")
    if platform.machine() != "arm64":
        raise SystemExit("expected an Apple Silicon (arm64) runner")


def build_icns(workdir: Path) -> Path:
    """Convert the Windows .ico to a macOS .icns via Pillow + iconutil."""
    from PIL import Image

    iconset = workdir / "HtmlNineFox.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    with Image.open(ICON_SOURCE) as frame:
        base = frame.convert("RGBA")
        for size in ICNS_SIZES:
            base.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
    icns = workdir / "HtmlNineFox.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns)],
        check=True,
    )
    return icns


def build_app(icns: Path) -> Path:
    dist_dir = BUILD / "dist"
    work_dir = BUILD / "work"
    spec_dir = BUILD / "spec"
    for directory in (dist_dir, work_dir, spec_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
         "--name", "HtmlNineFox", "--icon", str(icns),
         "--collect-all", "htmlninefox", "--collect-all", "playwright",
         "--distpath", str(dist_dir), "--workpath", str(work_dir), "--specpath", str(spec_dir),
         str(ENTRY)],
        cwd=ROOT,
        check=True,
    )
    app = dist_dir / "HtmlNineFox.app"
    if not app.is_dir():
        raise SystemExit(f"PyInstaller did not produce {app}")
    return app


def write_readme(staging: Path) -> None:
    (staging / "使用说明.txt").write_text(
        "Html九尾狐 · macOS 便携版（Apple Silicon）\n\n"
        "1. 解压后把 HtmlNineFox.app 拖入「应用程序」（或保持在可写位置直接使用）。\n"
        "2. 首次打开：右键 HtmlNineFox.app →「打开」→ 再点「打开」（绕过 Gatekeeper，\n"
        "   本包未做 Apple 公证）。\n"
        "3. 启动后会自动打开浏览器；数据与产物保存在应用包内 user-data 文件夹。\n"
        "4. 若 8620 端口被占用，程序会自动选择下一个可用端口。\n"
        "5. PDF / PNG 导出优先使用本机 Chrome / Edge，也支持 playwright install chromium。\n\n"
        "命令行运行：HtmlNineFox.app/Contents/MacOS/HtmlNineFox --help\n",
        encoding="utf-8",
    )


def package(app: Path, release_version: str) -> Path:
    RELEASE.mkdir(parents=True, exist_ok=True)
    folder_name = f"HtmlNineFox-macOS-arm64-{release_version}"
    staging = BUILD / folder_name
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app, staging / "HtmlNineFox.app", symlinks=True)
    write_readme(staging)
    archive = RELEASE / f"{folder_name}.zip"
    if archive.exists():
        archive.unlink()
    # ditto preserves symlinks, executable bits, and bundle metadata.
    subprocess.run(
        ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", folder_name, str(archive)],
        cwd=BUILD,
        check=True,
    )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest().upper()
    archive.with_suffix(archive.suffix + ".sha256.txt").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    return archive


def main() -> None:
    require_macos()
    release_version = version()
    icns = build_icns(BUILD / "assets")
    app = build_app(icns)
    archive = package(app, release_version)
    print(f"macos={archive}")


if __name__ == "__main__":
    main()
