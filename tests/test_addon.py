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
BASE_INDEX = "sha256:5ded610a2804fb7a973d2cbe390df09ceb67f0d7f603bcacd21ebaaa5a8a9b62"


def test_addon_bundles_exact_reviewed_provider_source() -> None:
    for name in PROVIDER_FILES:
        assert (ADDON / "yoto" / name).read_bytes() == (ROOT / "yoto" / name).read_bytes()


def test_addon_is_separate_reversible_and_hot_backed_up() -> None:
    config = (ADDON / "config.yaml").read_text()

    assert "version: 2.9.13-yoto.12" in config
    assert "slug: music_assistant_yoto" in config
    assert "slug: music_assistant\n" not in config
    assert "stage: experimental" in config
    assert "backup: cold" not in config
    assert not (ADDON / "build.yaml").exists()


def test_image_pins_official_2913_index_and_checks_packaged_provider() -> None:
    dockerfile = (ADDON / "Dockerfile").read_text()

    assert f"2.9.13@{BASE_INDEX}" in dockerfile
    assert "ARG BUILD_VERSION=2.9.13-yoto.12" in dockerfile
    assert '"yoto-api==4.3.3"' in dockerfile
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
