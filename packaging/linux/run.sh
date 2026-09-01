#!/bin/sh
set -eu
BIN_DIR=${HTMLNINEFOX_BIN_DIR:-"$HOME/.local/bin"}
if [ ! -x "$BIN_DIR/htmlninefox-app" ]; then
  echo "尚未安装，请先运行 ./install.sh" >&2
  exit 1
fi
exec "$BIN_DIR/htmlninefox-app" "$@"
