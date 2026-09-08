"""Download an offline Linux wheelhouse for CPython 3.10-3.13."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "packaging" / "linux" / "wheels"

PURE_REQUIREMENTS = (
    "click>=8.1",
    "rich>=13.0",
    "markdown-it-py>=2.2",
    "mdurl>=0.1",
    "pygments>=2.13",
    "pyee>=13,<14",
    "typing-extensions>=4.2",
)

PLATFORMS = (
    ("manylinux2014_x86_64", "manylinux1_x86_64"),
    ("manylinux2014_aarch64", "manylinux2014_aarch64"),
)


def run(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "download", *args], check=True)


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    run(
        "--dest", str(DEST), "--only-binary=:all:",
        *PURE_REQUIREMENTS,
    )
    for platform, playwright_platform in PLATFORMS:
        run(
            "--dest", str(DEST), "--only-binary=:all:", "--no-deps",
            "--platform", playwright_platform, "--python-version", "3.10",
            "--implementation", "cp", "--abi", "none", "playwright>=1.40,<2",
        )
        for minor in range(10, 14):
            version = f"3.{minor}"
            abi = f"cp3{minor}"
            for requirement in ("pyyaml>=6.0", "greenlet>=3.1.1,<4"):
                run(
                    "--dest", str(DEST), "--only-binary=:all:", "--no-deps",
                    "--platform", platform, "--python-version", version,
                    "--implementation", "cp", "--abi", abi, requirement,
                )
    playwright_wheels = {path.name for path in DEST.glob("playwright-*.whl")}
    expected_tags = {playwright_platform for _, playwright_platform in PLATFORMS}
    missing_tags = {
        tag for tag in expected_tags if not any(tag in name for name in playwright_wheels)
    }
    if missing_tags:
        raise SystemExit(
            "missing Playwright wheels for: " + ", ".join(sorted(missing_tags))
        )
    print(f"wheelhouse={DEST} files={len(list(DEST.glob('*.whl')))}")


if __name__ == "__main__":
    main()
