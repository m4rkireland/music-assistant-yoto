"""Stable, URL-free Yoto catalogue records."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CatalogueTrack:
    """A playable track without its ephemeral stream URL."""

    item_id: str
    card_id: str
    chapter_key: str
    track_key: str
    title: str
    duration: int
    chapter_number: int
    track_number: int
    format: str | None = None
    channels: str | None = None
    artwork: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogueCard:
    """A Yoto card and its ordered playable tracks."""

    item_id: str
    title: str
    description: str | None = None
    author: str | None = None
    category: str | None = None
    artwork: str | None = None
    series_title: str | None = None
    series_order: int | None = None
    tracks: tuple[CatalogueTrack, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogueGroup:
    """An ordered Yoto library group."""

    item_id: str
    name: str
    card_ids: tuple[str, ...] = ()
    artwork: str | None = None


@dataclass(slots=True)
class Catalogue:
    """Snapshot of cards and groups from the Yoto family library."""

    cards: dict[str, CatalogueCard] = field(default_factory=dict)
    groups: dict[str, CatalogueGroup] = field(default_factory=dict)

    @classmethod
    def from_responses(
        cls,
        library: Mapping[str, Any],
        details: Mapping[str, Mapping[str, Any]],
        groups: list[Mapping[str, Any]] | None = None,
    ) -> Catalogue:
        """Parse API responses into a stable catalogue snapshot."""
        card_records: dict[str, CatalogueCard] = {}
        cards = library.get("cards")
        if not isinstance(cards, list):
            raise ValueError("Yoto library response has no cards list")
        for raw in cards:
            if not isinstance(raw, Mapping):
                continue
            card_id = _text(_child(raw, "cardId"))
            if not card_id:
                continue
            card_data = _mapping(_child(raw, "card"))
            metadata = _mapping(_child(card_data, "metadata"))
            cover = _mapping(_child(metadata, "cover"))
            tracks = _parse_tracks(card_id, details.get(card_id, {}))
            card_records[card_id] = CatalogueCard(
                item_id=card_id,
                title=_text(_child(card_data, "title")) or card_id,
                description=_optional_text(_child(metadata, "description")),
                author=_optional_text(_child(metadata, "author")),
                category=_optional_text(_child(metadata, "stories")),
                artwork=_optional_text(_child(cover, "imageL")),
                series_title=_optional_text(_child(cover, "seriestitle")),
                series_order=_optional_int(_child(cover, "seriesorder")),
                tracks=tracks,
            )
        group_records: dict[str, CatalogueGroup] = {}
        for raw_group in groups or []:
            group_id = _text(_child(raw_group, "id"))
            if not group_id:
                continue
            ids = tuple(
                card_id
                for item in raw_group.get("items", [])
                if isinstance(item, Mapping)
                and (card_id := _text(_child(item, "contentId")))
            )
            group_records[group_id] = CatalogueGroup(
                item_id=group_id,
                name=_text(_child(raw_group, "name")) or group_id,
                card_ids=ids,
                artwork=_optional_text(_child(raw_group, "imageUrl")),
            )
        return cls(card_records, group_records)

    def find_track(self, item_id: str) -> CatalogueTrack | None:
        """Find one track by stable provider ID."""
        try:
            card_id, _, _ = decode_track_id(item_id)
        except ValueError:
            return None
        card = self.cards.get(card_id)
        if card is None:
            return None
        return next((track for track in card.tracks if track.item_id == item_id), None)


def encode_track_id(card_id: str, chapter_key: str, track_key: str) -> str:
    """Encode Yoto's three-part track identity as a URL-safe provider ID."""
    payload = json.dumps([card_id, chapter_key, track_key], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_track_id(item_id: str) -> tuple[str, str, str]:
    """Decode a provider track ID into its Yoto identity."""
    try:
        payload = base64.urlsafe_b64decode(item_id + "=" * (-len(item_id) % 4))
        values = json.loads(payload)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ValueError("Invalid Yoto track ID") from err
    if not isinstance(values, list) or len(values) != 3 or not all(
        isinstance(value, str) and value for value in values
    ):
        raise ValueError("Invalid Yoto track ID")
    return values[0], values[1], values[2]


def _parse_tracks(card_id: str, detail: Mapping[str, Any]) -> tuple[CatalogueTrack, ...]:
    card = _mapping(_child(detail, "card"))
    content = _mapping(_child(card, "content"))
    chapters = content.get("chapters", [])
    if not isinstance(chapters, list):
        return ()
    result: list[CatalogueTrack] = []
    for chapter_number, raw_chapter in enumerate(chapters, 1):
        if not isinstance(raw_chapter, Mapping):
            continue
        chapter_key = _text(_child(raw_chapter, "key"))
        if not chapter_key:
            continue
        chapter_artwork = _optional_text(
            _child(_mapping(_child(raw_chapter, "display")), "icon16x16")
        )
        raw_tracks = raw_chapter.get("tracks", [])
        if not isinstance(raw_tracks, list):
            continue
        for raw_track in raw_tracks:
            if not isinstance(raw_track, Mapping):
                continue
            track_key = _text(_child(raw_track, "key"))
            if not track_key or _optional_text(_child(raw_track, "type")) not in (None, "audio"):
                continue
            result.append(
                CatalogueTrack(
                    item_id=encode_track_id(card_id, chapter_key, track_key),
                    card_id=card_id,
                    chapter_key=chapter_key,
                    track_key=track_key,
                    title=_text(_child(raw_track, "title")) or track_key,
                    duration=_optional_int(_child(raw_track, "duration")) or 0,
                    chapter_number=chapter_number,
                    track_number=len(result) + 1,
                    format=_optional_text(_child(raw_track, "format")),
                    channels=_optional_text(_child(raw_track, "channels")),
                    artwork=_optional_text(
                        _child(_mapping(_child(raw_track, "display")), "icon16x16")
                    )
                    or chapter_artwork,
                )
            )
    return tuple(result)


def _child(value: Mapping[str, Any], key: str) -> Any:
    child = value.get(key)
    if isinstance(child, Mapping) and set(child) == {"value"}:
        return child["value"]
    return child


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _optional_text(value: Any) -> str | None:
    return text if (text := _text(value)) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
