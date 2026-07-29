#!/usr/bin/env bash
set -euo pipefail

MA_SERVER=${1:-/home/dave/work/music-assistant-yoto-reference/server}
TARGET="$MA_SERVER/music_assistant/providers/yoto"

if [[ -L "$TARGET" ]]; then
  rm "$TARGET"
  echo "Removed isolated Yoto provider symlink: $TARGET"
elif [[ -e "$TARGET" ]]; then
  echo "Refusing to remove non-symlink path $TARGET" >&2
  exit 1
else
  echo "No isolated Yoto provider symlink present"
fi
