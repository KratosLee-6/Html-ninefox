#!/bin/sh
set -eu
PREFIX=${HTMLNINEFOX_PREFIX:-"$HOME/.local/share/htmlninefox"}
BIN_DIR=${HTMLNINEFOX_BIN_DIR:-"$HOME/.local/bin"}
DESKTOP_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
rm -rf "$PREFIX"
rm -f "$BIN_DIR/htmlninefox-app" "$BIN_DIR/htmlninefox" "$DESKTOP_DIR/htmlninefox.desktop"
echo "Html九尾狐已从当前用户目录卸载。"
