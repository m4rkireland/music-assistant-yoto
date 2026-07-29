from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

MA_SERVER = Path("/home/dave/work/music-assistant-yoto-reference/server")


def _namespace(name: str, path: Path) -> None:
    module = ModuleType(name)
    module.__path__ = [str(path)]  # type: ignore[attr-defined]
    sys.modules[name] = module


# Load the exact 2.9.9 provider interfaces without executing the server package's
# eager application bootstrap (which would require the full runtime dependency set).
_namespace("music_assistant", MA_SERVER / "music_assistant")
_namespace("music_assistant.models", MA_SERVER / "music_assistant" / "models")
_namespace("music_assistant.controllers", MA_SERVER / "music_assistant" / "controllers")
_namespace(
    "music_assistant.controllers.tasks",
    MA_SERVER / "music_assistant" / "controllers" / "tasks",
)
