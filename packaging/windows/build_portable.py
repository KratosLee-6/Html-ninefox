"""Build the branded Windows portable package and optional Inno Setup installer."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = ROOT / "build" / "windows"
RELEASE_ROOT = ROOT / "release"


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def build_icon() -> Path:
    import cairosvg
    from PIL import Image

    asset_dir = BUILD_ROOT / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    png_path = asset_dir / "htmlninefox-256.png"
    ico_path = asset_dir / "htmlninefox.ico"
    cairosvg.svg2png(
        url=str(ROOT / "htmlninefox" / "server" / "static" / "icon.svg"),
        write_to=str(png_path),
        output_width=256,
        output_height=256,
    )
    with Image.open(png_path) as image:
        image.save(ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ico_path


def build_portable() -> tuple[Path, Path]:
    release_version = version()
    icon_path = build_icon()
    dist_dir = BUILD_ROOT / "dist"
    work_dir = BUILD_ROOT / "work"
    spec_dir = BUILD_ROOT / "spec"
    for directory in (dist_dir, work_dir, spec_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
        "--name", "HtmlNineFox", "--icon", str(icon_path), "--collect-all", "htmlninefox",
        "--distpath", str(dist_dir), "--workpath", str(work_dir), "--specpath", str(spec_dir),
        str(ROOT / "packaging" / "windows" / "launcher.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    app_dir = dist_dir / "HtmlNineFox"
    (app_dir / "START-HERE.txt").write_text(
        "Html九尾狐 · Windows 便携版\n\n双击 HtmlNineFox.exe 即可启动，浏览器会自动打开。\n"
        "数据与产物保存在当前目录的 user-data 文件夹。\n"
        "若 8620 端口已占用，程序会自动选择后续可用端口。\n",
        encoding="utf-8",
    )
    (app_dir / "启动Html九尾狐.cmd").write_text(
        '@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\nHtmlNineFox.exe\r\n', encoding="utf-8"
    )
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    archive = RELEASE_ROOT / f"HtmlNineFox-Windows-x64-{release_version}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for item in sorted(app_dir.rglob("*")):
            if item.is_file():
                package.write(item, Path(f"HtmlNineFox-Windows-x64-{release_version}") / item.relative_to(app_dir))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest().upper()
    checksum = archive.with_suffix(archive.suffix + ".sha256.txt")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return app_dir, archive


def build_installer(app_dir: Path) -> Path | None:
    iscc = shutil.which("iscc")
    if not iscc:
        return None
    release_version = version()
    output_dir = RELEASE_ROOT.resolve()
    icon_path = (BUILD_ROOT / "assets" / "htmlninefox.ico").resolve()
    command = [
        iscc, f"/DMyVersion={release_version}", f"/DSourceDir={app_dir.resolve()}",
        f"/DOutputDir={output_dir}", f"/DIconFile={icon_path}",
        str(ROOT / "packaging" / "windows" / "HtmlNineFox.iss"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return output_dir / f"HtmlNineFox-Setup-{release_version}.exe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", action="store_true", help="检测到 Inno Setup 时继续构建安装器")
    args = parser.parse_args()
    app_dir, archive = build_portable()
    print(f"portable={archive}")
    if args.installer:
        installer = build_installer(app_dir)
        print(f"installer={installer or 'skipped: iscc not found'}")


if __name__ == "__main__":
    main()
