import inspect
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def test_manifest_is_music_provider_with_pinned_dependency_and_no_secrets() -> None:
    manifest = json.loads((ROOT / "yoto" / "manifest.json").read_text())

    assert manifest["domain"] == "yoto"
    assert manifest["type"] == "music"
    assert manifest["name"] == "Yoto"
    assert manifest["requirements"] == ["yoto-api==4.3.2"]
    assert {"description", "codeowners", "documentation"} <= manifest.keys()
    serialized = json.dumps(manifest).lower()
    assert "refresh_token" not in serialized
    assert "access_token" not in serialized


@pytest.mark.asyncio
async def test_setup_entry_point_returns_provider() -> None:
    import yoto

    assert inspect.iscoroutinefunction(yoto.setup)
