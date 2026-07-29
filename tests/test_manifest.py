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
    assert manifest["stage"] == "experimental"
    assert manifest["multi_instance"] is True
    assert manifest["requirements"] == ["yoto-api==4.3.2"]
    assert {"description", "codeowners", "documentation"} <= manifest.keys()
    serialized = json.dumps(manifest).lower()
    assert "refresh_token" not in serialized
    assert "access_token" not in serialized


@pytest.mark.asyncio
async def test_setup_entry_point_returns_provider() -> None:
    import yoto

    assert inspect.iscoroutinefunction(yoto.setup)


def test_public_files_are_environment_agnostic_and_current() -> None:
    public_files = [
        ROOT / "README.md",
        *(ROOT / "docs").glob("*.md"),
        *(ROOT / "scripts").glob("*.sh"),
        ROOT / "tests" / "conftest.py",
        ROOT / "music_assistant_yoto" / "README.md",
        ROOT / "music_assistant_yoto" / "Dockerfile",
        ROOT / "music_assistant_yoto" / "config.yaml",
    ]
    combined = "\n".join(path.read_text() for path in public_files if path.exists()).casefold()
    readme = (ROOT / "README.md").read_text().casefold()

    assert "/home/" not in combined
    assert "nfc" not in combined
    assert "tag player" not in combined
    assert "every yoto card is represented as a music assistant album" in readme
    assert "native audiobook representation" in readme
    assert "not implemented" in readme
    assert "story and sleep cards represented as seekable audiobooks" not in combined
