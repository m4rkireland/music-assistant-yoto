#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MA_SERVER=${1:-/home/dave/work/music-assistant-yoto-reference/server}
TARGET="$MA_SERVER/music_assistant/providers/yoto"

if [[ ! -f "$MA_SERVER/music_assistant/models/music_provider.py" ]]; then
  echo "Music Assistant source not found at $MA_SERVER" >&2
  exit 1
fi
if [[ "$MA_SERVER" == *"/addon_configs/"* || "$MA_SERVER" == *"/config/"* ]]; then
  echo "Refusing to install into a production/add-on path" >&2
  exit 1
fi
if [[ "$(git -C "$MA_SERVER" describe --tags --exact-match 2>/dev/null || true)" != "2.9.9" ]]; then
  echo "The isolated source checkout must be exactly tag 2.9.9" >&2
  exit 1
fi
if [[ -e "$TARGET" && ! -L "$TARGET" ]]; then
  echo "Refusing to replace non-symlink path $TARGET" >&2
  exit 1
fi

ln -sfn "$ROOT/yoto" "$TARGET"
echo "Installed reversible isolated symlink: $TARGET -> $ROOT/yoto"
