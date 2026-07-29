from __future__ import annotations

import logging
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest
from music_assistant_models.enums import ContentType, MediaType, StreamType
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.streamdetails import MultiPartPath

from yoto.catalogue import Catalogue, CatalogueCard, CatalogueTrack, encode_track_id
from yoto.client import YotoAdapter
from yoto.provider import YotoProvider


@dataclass
class FakeTrack:
    key: str
    title: str = "Moon Story"
    duration: int = 42
    format: str = "aac"
    channels: str = "stereo"
    trackUrl: str | None = None
    icon: str | None = None
    type: str = "audio"


@dataclass
class FakeChapter:
    key: str
    tracks: dict[str, FakeTrack] = field(default_factory=dict)


@dataclass
class FakeCard:
    id: str
    chapters: dict[str, FakeChapter] = field(default_factory=dict)


@dataclass
class FakeToken:
    refresh_token: str = "fixture-refresh"


class FakeStreamAPI:
    def __init__(self) -> None:
        self.token = FakeToken()
        self.library: dict[str, Any] = {
            "card-alpha": FakeCard(
                "card-alpha",
                {
                    "chapter-a": FakeChapter(
                        "chapter-a",
                        {
                            "track-a": FakeTrack("track-a", duration=42),
                            "track-b": FakeTrack("track-b", title="Moon Ending", duration=18),
                        },
                    )
                },
            )
        }
        self.groups: dict[str, Any] = {}
        self.detail_calls = 0

    def set_refresh_token(self, refresh_token: str) -> None:
        self.token = FakeToken(refresh_token)

    async def check_and_refresh_token(self) -> FakeToken:
        return self.token

    async def update_card_detail(self, card_id: str) -> None:
        self.detail_calls += 1
        for track in self.library[card_id].chapters["chapter-a"].tracks.values():
            track.trackUrl = (
                f"https://secure-media.example/{track.key}.m4a?"
                f"signature=fixture-{self.detail_calls}"
            )


def _provider(adapter: YotoAdapter, item_id: str, *, category: str | None = None) -> YotoProvider:
    provider = object.__new__(YotoProvider)
    provider.config = SimpleNamespace(instance_id="yoto-instance")
    provider.adapter = adapter
    provider.catalogue = Catalogue(
        cards={
            "card-alpha": CatalogueCard(
                item_id="card-alpha",
                title="Moshi Moon",
                tracks=(
                    CatalogueTrack(
                        item_id=item_id,
                        card_id="card-alpha",
                        chapter_key="chapter-a",
                        track_key="track-a",
                        title="Moon Story",
                        chapter_title="Moon Chapter",
                        duration=42,
                        chapter_number=1,
                        track_number=1,
                        format="aac",
                    ),
                    CatalogueTrack(
                        item_id=encode_track_id("card-alpha", "chapter-a", "track-b"),
                        card_id="card-alpha",
                        chapter_key="chapter-a",
                        track_key="track-b",
                        title="Moon Ending",
                        chapter_title="Moon Chapter",
                        duration=18,
                        chapter_number=1,
                        track_number=2,
                        format="aac",
                    ),
                ),
                category=category,
            )
        }
    )
    return provider


@pytest.mark.asyncio
async def test_stream_resolution_refetches_each_time_and_returns_http_aac_details() -> None:
    api = FakeStreamAPI()
    adapter = YotoAdapter("fixture-client", "fixture-refresh", api=api)
    item_id = encode_track_id("card-alpha", "chapter-a", "track-a")
    provider = _provider(adapter, item_id)

    first = await provider.get_stream_details(item_id, MediaType.TRACK)
    second = await provider.get_stream_details(item_id, MediaType.TRACK)

    assert api.detail_calls == 2
    assert first.stream_type is StreamType.HTTP
    assert first.audio_format.content_type is ContentType.AAC
    assert first.duration == 42
    assert first.path != second.path
    assert "signature=fixture-1" in str(first.path)
    assert "signature=fixture-2" in str(second.path)


@pytest.mark.asyncio
async def test_signed_stream_is_not_added_to_catalogue_metadata_or_logs(caplog) -> None:
    api = FakeStreamAPI()
    adapter = YotoAdapter("fixture-client", "fixture-refresh", api=api)
    item_id = encode_track_id("card-alpha", "chapter-a", "track-a")
    provider = _provider(adapter, item_id)

    with caplog.at_level(logging.DEBUG):
        details = await provider.get_stream_details(item_id, MediaType.TRACK)

    assert details.path
    assert "secure-media" not in repr(provider.catalogue)
    assert "signature=" not in caplog.text
    assert "secure-media" not in caplog.text


@pytest.mark.asyncio
async def test_audiobook_stream_resolves_all_parts_fresh_with_seekable_combined_timeline() -> None:
    api = FakeStreamAPI()
    adapter = YotoAdapter("fixture-client", "fixture-refresh", api=api)
    item_id = encode_track_id("card-alpha", "chapter-a", "track-a")
    provider = _provider(adapter, item_id, category="stories")

    first = await provider.get_stream_details("card-alpha", MediaType.AUDIOBOOK)
    second = await provider.get_stream_details("card-alpha", MediaType.AUDIOBOOK)

    assert api.detail_calls == 2
    assert first.media_type is MediaType.AUDIOBOOK
    assert first.stream_type is StreamType.HTTP
    assert first.duration == 60
    assert first.allow_seek
    assert first.can_seek
    assert isinstance(first.path, list)
    assert all(isinstance(part, MultiPartPath) for part in first.path)
    assert [part.duration for part in first.path] == [42, 18]
    assert [part.path.split("?", 1)[0].rsplit("/", 1)[-1] for part in first.path] == [
        "track-a.m4a",
        "track-b.m4a",
    ]
    assert first.path != second.path


@pytest.mark.asyncio
async def test_stream_resolution_rejects_wrong_type_missing_track_and_missing_url() -> None:
    api = FakeStreamAPI()
    adapter = YotoAdapter("fixture-client", "fixture-refresh", api=api)
    item_id = encode_track_id("card-alpha", "chapter-a", "track-a")
    provider = _provider(adapter, item_id)

    with pytest.raises(MediaNotFoundError):
        await provider.get_stream_details(item_id, MediaType.ALBUM)
    with pytest.raises(MediaNotFoundError):
        await provider.get_stream_details("not-a-track", MediaType.TRACK)

    async def no_url(_card_id: str) -> None:
        api.detail_calls += 1

    api.update_card_detail = no_url  # type: ignore[method-assign]
    api.library["card-alpha"].chapters["chapter-a"].tracks["track-a"].trackUrl = None
    with pytest.raises(MediaNotFoundError, match="stream is unavailable"):
        await provider.get_stream_details(item_id, MediaType.TRACK)
