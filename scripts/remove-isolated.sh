#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MA_SERVER=${1:-${MA_SERVER:-$ROOT/.music-assistant-server}}
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
