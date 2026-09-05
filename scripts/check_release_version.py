"""Fail fast when release metadata drifts across source and packaging."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("version missing from pyproject.toml")
    return match.group(1)


def package_version() -> str:
    text = (ROOT / "htmlninefox" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("__version__ missing from htmlninefox/__init__.py")
    return match.group(1)


def require_text(relative: str, expected: str) -> None:
    text = (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")
    if expected not in text:
        raise SystemExit(f"{relative} is missing expected release metadata: {expected}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Git tag to compare, for example v0.4.1")
    args = parser.parse_args()

    version = project_version()
    source_version = package_version()
    if source_version != version:
        raise SystemExit(
            f"package version mismatch: pyproject={version}, htmlninefox={source_version}"
        )
    if args.tag and args.tag.removeprefix("v") != version:
        raise SystemExit(f"tag mismatch: tag={args.tag}, package=v{version}")

    require_text("README.md", f"releases/tag/v{version}")
    require_text("README.en.md", f"releases/tag/v{version}")
    require_text("uv.lock", f'name = "htmlninefox"\nversion = "{version}"')
    require_text("packaging/linux/install.sh", "__HTMLNINEFOX_VERSION__")
    print(f"release metadata consistent: v{version}")


if __name__ == "__main__":
    main()
