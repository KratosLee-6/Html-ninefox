"""Desktop/portable executable entry point."""

from __future__ import annotations

import argparse

from .launcher import frozen_portable_root, launch_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Html九尾狐 · Pixel Garden 工作台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8620)
    parser.add_argument("--output")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--strict-port", action="store_true")
    parser.add_argument("--user-data", action="store_true", help="冻结包也使用用户目录，不写入便携目录")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    portable_root = None if args.user_data else frozen_portable_root()
    launch_workspace(
        args.host,
        args.port,
        args.output,
        open_browser=not args.no_browser,
        fallback_port=not args.strict_port,
        portable_root=portable_root,
        distribution="windows-portable" if portable_root else "python-app",
    )


if __name__ == "__main__":
    main()
