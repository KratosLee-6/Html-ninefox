#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
if ! command -v uv >/dev/null 2>&1; then
  echo "未找到 uv；请使用 Linux .run 安装包或 Docker。" >&2
  exit 1
fi
exec uv run htmlninefox app
