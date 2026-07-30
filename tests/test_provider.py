from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.enums import MediaType
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.media_items import Album, Audiobook, BrowseFolder

import yoto.provider as provider_module
from yoto.catalogue import Catalogue, CatalogueGroup
from yoto.provider import YotoProvider

FIXTURES = Path(__file__).parent / "fixtures"


def _catalogue() -> Catalogue:
    library = json.loads((FIXTURES / "library.json").read_text())
    detail = json.loads((FIXTURES / "card_detail.json").read_text())
    result = Catalogue.from_responses(library, {"card-alpha": detail})
    result.groups["bedtime"] = CatalogueGroup(
        item_id="bedtime", name="Bedtime", card_ids=("card-alpha", "missing-card")
    )
    return result


def _provider() -> YotoProvider:
    provider = object.__new__(YotoProvider)
    provider.config = SimpleNamespace(instance_id="yoto-instance")
    provider.catalogue = _catalogue()
    return provider


@pytest.mark.asyncio
async def test_search_matches_card_track_author_and_series_and_honours_media_types() -> None:
    provider = _provider()

    moshi = await provider.search(
        "moshi", [MediaType.ALBUM, MediaType.AUDIOBOOK, MediaType.TRACK], limit=10
    )
    track_title = await provider.search("second", [MediaType.TRACK], limit=10)
    author = await provider.search("dream reader", [MediaType.AUDIOBOOK], limit=10)

    assert not moshi.albums
    assert [book.name for book in moshi.audiobooks] == ["Moshi Moon"]
    assert not moshi.tracks
    assert not track_title.tracks
    assert [book.name for book in author.audiobooks] == ["Moshi Moon"]
    assert not author.tracks


@pytest.mark.asyncio
async def test_search_is_case_insensitive_and_applies_per_type_limit() -> None:
    provider = _provider()

    result = await provider.search(
        "M", [MediaType.ALBUM, MediaType.AUDIOBOOK, MediaType.TRACK], limit=1
    )

    assert len(result.albums) <= 1
    assert len(result.audiobooks) <= 1
    assert len(result.tracks) <= 1


@pytest.mark.asyncio
async def test_browse_exposes_all_cards_and_groups_and_skips_stale_group_members() -> None:
    provider = _provider()

    root = await provider.browse("yoto-instance://")
    cards = await provider.browse("yoto-instance://cards")
    groups = await provider.browse("yoto-instance://groups")
    grouped = await provider.browse("yoto-instance://group/bedtime")

    assert [item.name for item in root if isinstance(item, BrowseFolder)] == [
        "All Yoto cards",
        "Yoto library groups",
    ]
    assert [item.name for item in cards] == ["Moshi Moon", "Rain Songs"]
    assert isinstance(cards[0], Audiobook)
    assert isinstance(cards[1], Album)
    assert [item.name for item in groups if isinstance(item, BrowseFolder)] == ["Bedtime"]
    assert [item.name for item in grouped if isinstance(item, Audiobook)] == ["Moshi Moon"]


@pytest.mark.asyncio
async def test_library_generators_separate_story_audiobooks_from_music_albums_and_tracks() -> None:
    provider = _provider()

    audiobooks = [item async for item in provider.get_library_audiobooks()]
    albums = [item async for item in provider.get_library_albums()]
    tracks = [item async for item in provider.get_library_tracks()]

    assert [item.name for item in audiobooks] == ["Moshi Moon"]
    assert [item.name for item in albums] == ["Rain Songs"]
    assert tracks == []


@pytest.mark.asyncio
async def test_direct_getters_enforce_audiobook_and_album_media_types() -> None:
    provider = _provider()

    audiobook = await provider.get_audiobook("card-alpha")
    album = await provider.get_album("card-beta")

    assert audiobook.media_type is MediaType.AUDIOBOOK
    assert album.media_type is MediaType.ALBUM
    with pytest.raises(MediaNotFoundError):
        await provider.get_audiobook("card-beta")
    with pytest.raises(MediaNotFoundError):
        await provider.get_album("card-alpha")


@pytest.mark.asyncio
async def test_browse_rejects_unknown_paths() -> None:
    with pytest.raises(MediaNotFoundError):
        await _provider().browse("yoto-instance://unknown")


@pytest.mark.asyncio
async def test_library_sync_refreshes_yoto_catalogue_before_import(monkeypatch) -> None:
    provider = _provider()
    refreshed = Catalogue()
    provider.adapter = SimpleNamespace(refresh_catalogue=AsyncMock(return_value=refreshed))
    base_sync_calls: list[MediaType] = []

    async def fake_base_sync(_provider, media_type: MediaType) -> None:
        base_sync_calls.append(media_type)

    monkeypatch.setattr(MusicProvider, "sync_library", fake_base_sync)

    await provider.sync_library(MediaType.ALBUM)

    provider.adapter.refresh_catalogue.assert_awaited_once_with()
    assert provider.catalogue is refreshed
    assert base_sync_calls == [MediaType.ALBUM]


@pytest.mark.asyncio
async def test_concurrent_media_type_syncs_share_one_serialized_catalogue_refresh(
    monkeypatch,
) -> None:
    provider = _provider()
    refreshed = Catalogue()

    async def refresh_catalogue() -> Catalogue:
        await asyncio.sleep(0)
        return refreshed

    provider.adapter = SimpleNamespace(refresh_catalogue=AsyncMock(side_effect=refresh_catalogue))
    base_sync_calls: list[MediaType] = []

    async def fake_base_sync(_provider, media_type: MediaType) -> None:
        await asyncio.sleep(0)
        base_sync_calls.append(media_type)

    monkeypatch.setattr(MusicProvider, "sync_library", fake_base_sync)

    await asyncio.gather(
        provider.sync_library(MediaType.ALBUM),
        provider.sync_library(MediaType.TRACK),
        provider.sync_library(MediaType.AUDIOBOOK),
    )

    provider.adapter.refresh_catalogue.assert_awaited_once_with()
    assert provider.catalogue is refreshed
    assert set(base_sync_calls) == {MediaType.ALBUM, MediaType.TRACK, MediaType.AUDIOBOOK}


@pytest.mark.asyncio
async def test_sync_refreshes_at_the_thirty_second_freshness_boundary(monkeypatch) -> None:
    provider = _provider()
    provider._sync_lock = asyncio.Lock()
    provider._last_sync_refresh = 100.0
    refreshed = Catalogue()
    provider.adapter = SimpleNamespace(refresh_catalogue=AsyncMock(return_value=refreshed))
    monotonic_values = iter((129.9, 130.0, 130.1))
    monkeypatch.setattr(provider_module, "monotonic", lambda: next(monotonic_values))

    async def fake_base_sync(_provider, _media_type: MediaType) -> None:
        return None

    monkeypatch.setattr(MusicProvider, "sync_library", fake_base_sync)

    await provider.sync_library(MediaType.ALBUM)
    provider.adapter.refresh_catalogue.assert_not_awaited()

    await provider.sync_library(MediaType.AUDIOBOOK)
    provider.adapter.refresh_catalogue.assert_awaited_once_with()
    assert provider.catalogue is refreshed
    assert provider._last_sync_refresh == 130.1


@pytest.mark.asyncio
async def test_unload_revokes_playback_sessions_and_unregisters_route(monkeypatch) -> None:
    provider = _provider()
    callback_calls = 0

    def unregister_route() -> None:
        nonlocal callback_calls
        callback_calls += 1

    provider._audiobook_sessions = {"opaque-session": object()}  # type: ignore[dict-item]
    provider._on_unload_callbacks = [unregister_route]

    async def fake_base_unload(_provider, _is_removed: bool = False) -> None:
        return None

    monkeypatch.setattr(MusicProvider, "unload", fake_base_unload)

    await provider.unload()

    assert provider._audiobook_sessions == {}
    assert callback_calls == 1
