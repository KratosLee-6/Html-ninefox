"""Build Linux tar.gz and self-extracting .run installers."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"
BUILD = ROOT / "build" / "linux"
TEMPLATES = ROOT / "packaging" / "linux"


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("version missing from pyproject.toml")
    return match.group(1)


def checksum(target: Path) -> str:
    digest = hashlib.sha256(target.read_bytes()).hexdigest().upper()
    target.with_suffix(target.suffix + ".sha256.txt").write_text(
        f"{digest}  {target.name}\n", encoding="ascii"
    )
    return digest


def main() -> None:
    release_version = version()
    wheel = ROOT / "dist" / f"htmlninefox-{release_version}-py3-none-any.whl"
    if not wheel.exists():
        raise SystemExit(f"missing wheel: {wheel}")
    package_name = f"HtmlNineFox-Linux-{release_version}"
    staging = BUILD / package_name
    if BUILD.exists():
        shutil.rmtree(BUILD)
    staging.mkdir(parents=True)
    for name in ("install.sh", "run.sh", "uninstall.sh", "README.md"):
        shutil.copy2(TEMPLATES / name, staging / name)
    install_script = staging / "install.sh"
    install_script.write_text(
        install_script.read_text(encoding="utf-8").replace(
            "__HTMLNINEFOX_VERSION__", release_version
        ),
        encoding="utf-8",
        newline="\n",
    )
    shutil.copy2(wheel, staging / wheel.name)
    shutil.copy2(ROOT / "htmlninefox" / "server" / "static" / "icon.svg", staging / "icon.svg")
    wheelhouse = TEMPLATES / "wheels"
    if wheelhouse.exists():
        shutil.copytree(wheelhouse, staging / "wheels")
    for name in ("install.sh", "run.sh", "uninstall.sh"):
        os.chmod(staging / name, 0o755)
    RELEASE.mkdir(parents=True, exist_ok=True)
    release_wheel = RELEASE / wheel.name
    shutil.copy2(wheel, release_wheel)
    checksum(release_wheel)
    archive = RELEASE / f"{package_name}.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as package:
        package.add(staging, arcname=package_name)
    run_path = RELEASE / f"{package_name}.run"
    header = (
        "#!/bin/sh\n"
        "set -eu\n"
        "ARCHIVE_LINE=$(awk '/^__HTMLNINEFOX_ARCHIVE__$/ {print NR + 1; exit}' \"$0\")\n"
        "TMP_BASE=\"${TMPDIR:-/tmp}\"\n"
        "TMP_ROOT=$(mktemp -d \"$TMP_BASE/htmlninefox.XXXXXX\")\n"
        "trap 'rm -rf \"$TMP_ROOT\"' EXIT HUP INT TERM\n"
        "tail -n +\"$ARCHIVE_LINE\" \"$0\" | tar -xz -C \"$TMP_ROOT\"\n"
        f"exec \"$TMP_ROOT/{package_name}/install.sh\" \"$@\"\n"
        "__HTMLNINEFOX_ARCHIVE__\n"
    ).encode("utf-8")
    run_path.write_bytes(header + archive.read_bytes())
    os.chmod(run_path, 0o755)
    print(f"archive={archive} sha256={checksum(archive)}")
    print(f"installer={run_path} sha256={checksum(run_path)}")


if __name__ == "__main__":
    main()
