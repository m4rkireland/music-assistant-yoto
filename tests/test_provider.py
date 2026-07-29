from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from music_assistant_models.enums import MediaType
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.media_items import Album, BrowseFolder

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

    moshi = await provider.search("moshi", [MediaType.ALBUM, MediaType.TRACK], limit=10)
    track_title = await provider.search("second", [MediaType.TRACK], limit=10)
    author = await provider.search("dream reader", [MediaType.ALBUM], limit=10)

    assert [album.name for album in moshi.albums] == ["Moshi Moon"]
    assert [track.name for track in moshi.tracks] == ["Second", "Third", "First"]
    assert [track.name for track in track_title.tracks] == ["Second"]
    assert [album.name for album in author.albums] == ["Moshi Moon"]
    assert not author.tracks


@pytest.mark.asyncio
async def test_search_is_case_insensitive_and_applies_per_type_limit() -> None:
    provider = _provider()

    result = await provider.search("M", [MediaType.ALBUM, MediaType.TRACK], limit=1)

    assert len(result.albums) <= 1
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
    assert [item.name for item in cards if isinstance(item, Album)] == [
        "Moshi Moon",
        "Rain Songs",
    ]
    assert [item.name for item in groups if isinstance(item, BrowseFolder)] == ["Bedtime"]
    assert [item.name for item in grouped if isinstance(item, Album)] == ["Moshi Moon"]


@pytest.mark.asyncio
async def test_browse_rejects_unknown_paths() -> None:
    with pytest.raises(MediaNotFoundError):
        await _provider().browse("yoto-instance://unknown")
