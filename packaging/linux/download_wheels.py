"""Download an offline Linux wheelhouse for CPython 3.10-3.13."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "packaging" / "linux" / "wheels"


def run(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "download", *args], check=True)


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    run(
        "--dest", str(DEST), "--only-binary=:all:",
        "click>=8.1", "rich>=13.0", "markdown-it-py>=2.2", "mdurl>=0.1", "pygments>=2.13",
    )
    for platform in ("manylinux2014_x86_64", "manylinux2014_aarch64"):
        for minor in range(10, 14):
            version = f"3.{minor}"
            abi = f"cp3{minor}"
            run(
                "--dest", str(DEST), "--only-binary=:all:", "--no-deps",
                "--platform", platform, "--python-version", version,
                "--implementation", "cp", "--abi", abi, "pyyaml>=6.0",
            )
    print(f"wheelhouse={DEST} files={len(list(DEST.glob('*.whl')))}")


if __name__ == "__main__":
    main()
