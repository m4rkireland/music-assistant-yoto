from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
ADDON = ROOT / "music_assistant_yoto"
PROVIDER_FILES = (
    "__init__.py",
    "client.py",
    "catalogue.py",
    "provider.py",
    "pkce.py",
    "manifest.json",
)
BASE_INDEX = "sha256:50666a6f8d7f87d53d993dc41860ab06dda11047f6e433bb5bdbcb6e309ac74c"


def test_addon_bundles_exact_reviewed_provider_source() -> None:
    for name in PROVIDER_FILES:
        assert (ADDON / "yoto" / name).read_bytes() == (ROOT / "yoto" / name).read_bytes()


def test_addon_is_separate_reversible_and_cold_backed_up() -> None:
    config = (ADDON / "config.yaml").read_text()

    assert "version: 2.9.9-yoto.7" in config
    assert "slug: music_assistant_yoto" in config
    assert "slug: music_assistant\n" not in config
    assert "stage: experimental" in config
    assert "backup: cold" in config
    assert not (ADDON / "build.yaml").exists()


def test_image_pins_official_299_index_and_checks_packaged_provider() -> None:
    dockerfile = (ADDON / "Dockerfile").read_text()

    assert f"2.9.9@{BASE_INDEX}" in dockerfile
    assert '"yoto-api==4.3.2"' in dockerfile
    assert "manifest.json" in dockerfile
    assert 'io.hass.type="app"' in dockerfile
    for name in ("client.py", "catalogue.py", "provider.py", "pkce.py"):
        assert name in dockerfile


def test_repository_metadata_and_required_artwork_are_present() -> None:
    repository = (ROOT / "repository.yaml").read_text()

    assert "m4rkireland/music-assistant-yoto" in repository
    assert (ADDON / "icon.png").is_file()
    assert (ADDON / "logo.png").is_file()
    assert (ADDON / "CHANGELOG.md").is_file()
