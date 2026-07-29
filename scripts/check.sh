#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MA_SERVER=${MA_SERVER:-/home/dave/work/music-assistant-yoto-reference/server}
VENV=${VENV:-$ROOT/.venv}

if [[ ! -f "$MA_SERVER/music_assistant/models/music_provider.py" ]]; then
  echo "Music Assistant source not found at $MA_SERVER" >&2
  exit 1
fi

actual_tag=$(git -C "$MA_SERVER" describe --tags --exact-match 2>/dev/null || true)
if [[ "$actual_tag" != "2.9.9" ]]; then
  echo "Expected Music Assistant tag 2.9.9, found ${actual_tag:-untagged}" >&2
  exit 1
fi

"$VENV/bin/ruff" format --check "$ROOT"
"$VENV/bin/ruff" check "$ROOT"
"$VENV/bin/mypy" "$ROOT/yoto"
"$VENV/bin/pytest" -q "$ROOT/tests"

PYTHONPATH="$MA_SERVER" "$VENV/bin/python" - <<'PY'
import importlib
import json
from pathlib import Path

provider = importlib.import_module("yoto")
manifest = json.loads((Path(provider.__file__).parent / "manifest.json").read_text())
assert manifest["domain"] == "yoto"
assert manifest["requirements"] == ["yoto-api==4.3.2"]
assert callable(provider.setup)
assert callable(provider.get_config_entries)
print("Music Assistant 2.9.9 provider contract import: PASS")
PY
