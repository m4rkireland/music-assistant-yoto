"""Music Assistant mapping and provider implementation."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

from aiohttp import web
from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.enums import (
    ContentType,
    ImageType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import MediaNotFoundError, ProviderUnavailableError
from music_assistant_models.media_items import (
    Album,
    Artist,
    Audiobook,
    AudioFormat,
    BrowseFolder,
    ItemMapping,
    MediaItemChapter,
    MediaItemImage,
    ProviderMapping,
    SearchResults,
    Track,
    UniqueList,
)
from music_assistant_models.streamdetails import MultiPartPath, StreamDetails

from .catalogue import Catalogue, CatalogueCard, CatalogueTrack

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from .client import YotoAdapter

SUPPORTED_FEATURES = {
    ProviderFeature.BROWSE,
    ProviderFeature.SEARCH,
    ProviderFeature.LIBRARY_ALBUMS,
    ProviderFeature.LIBRARY_AUDIOBOOKS,
    ProviderFeature.LIBRARY_TRACKS,
}

SYNC_REFRESH_WINDOW = 30
MIN_PLAYBACK_SESSION_TTL = 15 * 60
PLAYBACK_SESSION_BUFFER = 15 * 60
MAX_PLAYBACK_SESSIONS = 64


@dataclass(slots=True)
class _AudiobookPlaybackSession:
    """Short-lived capability for one audiobook's ordered parts."""

    card_id: str
    part_ids: tuple[str, ...]
    expires_at: float


class YotoProvider(MusicProvider):
    """Read-only Yoto card library provider."""

    adapter: YotoAdapter

    def __init__(
        self, mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
    ) -> None:
        """Initialize an empty Yoto provider."""
        super().__init__(mass, manifest, config, SUPPORTED_FEATURES)
        self.catalogue = Catalogue()
        self._sync_lock = asyncio.Lock()
        self._last_sync_refresh = 0.0
        self._audiobook_sessions: dict[str, _AudiobookPlaybackSession] = {}

    async def handle_async_init(self) -> None:
        """Authenticate and load the initial family-library snapshot."""
        from . import CONF_CLIENT_ID, CONF_REFRESH_TOKEN
        from .client import YotoAdapter

        client_id = str(self.config.get_value(CONF_CLIENT_ID) or "")
        refresh_token = str(self.config.get_value(CONF_REFRESH_TOKEN) or "")
        self.adapter = YotoAdapter(
            client_id,
            refresh_token,
            session=self.mass.http_session,
            token_callback=self._persist_refresh_token,
        )
        self.catalogue = await self.adapter.refresh_catalogue()
        self._on_unload_callbacks = [
            self.mass.streams.register_dynamic_route(
                f"/{self.instance_id}_yoto_part", self._handle_audiobook_part_request
            )
        ]

    async def unload(self, is_removed: bool = False) -> None:
        """Unregister dynamic stream routes when the provider is unloaded."""
        self._audiobook_sessions.clear()
        for callback in getattr(self, "_on_unload_callbacks", []):
            callback()
        await super().unload(is_removed)

    async def _persist_refresh_token(self, refresh_token: str) -> None:
        """Persist a single-use rotated token before further API work."""
        from . import CONF_REFRESH_TOKEN

        self._update_config_value(CONF_REFRESH_TOKEN, refresh_token, encrypted=True)
        self.mass.config.save(immediate=True)

    @property
    def is_streaming_provider(self) -> bool:
        """Return whether this provider resolves remote streams."""
        return True

    async def sync_library(self, media_type: MediaType) -> None:
        """Refresh once for a burst of independent MA media-type syncs."""
        if not hasattr(self, "_sync_lock"):
            self._sync_lock = asyncio.Lock()
            self._last_sync_refresh = 0.0
        async with self._sync_lock:
            now = monotonic()
            if now - self._last_sync_refresh >= SYNC_REFRESH_WINDOW:
                self.catalogue = await self.adapter.refresh_catalogue()
                self._last_sync_refresh = monotonic()
            await super().sync_library(media_type)

    async def get_library_albums(self) -> AsyncGenerator[Album]:
        """Yield non-story cards as albums."""
        for card in self.catalogue.cards.values():
            if not card.is_audiobook:
                yield map_album(card, self.instance_id)

    async def get_library_audiobooks(self) -> AsyncGenerator[Audiobook]:
        """Yield story cards as resumable audiobooks."""
        for card in self.catalogue.cards.values():
            if card.is_audiobook:
                yield map_audiobook(card, self.instance_id)

    async def get_library_tracks(self) -> AsyncGenerator[Track]:
        """Yield every playable card track in source order."""
        for card in self.catalogue.cards.values():
            if card.is_audiobook:
                continue
            for track in card.tracks:
                yield map_track(card, track, self.instance_id)

    async def get_album(self, prov_album_id: str) -> Album:
        """Return one card as an album."""
        if (card := self.catalogue.cards.get(prov_album_id)) is None or card.is_audiobook:
            raise MediaNotFoundError(f"Yoto card {prov_album_id!r} is unavailable")
        return map_album(card, self.instance_id)

    async def get_audiobook(self, prov_audiobook_id: str) -> Audiobook:
        """Return one story card as an audiobook."""
        if (card := self.catalogue.cards.get(prov_audiobook_id)) is None or not card.is_audiobook:
            raise MediaNotFoundError(f"Yoto audiobook {prov_audiobook_id!r} is unavailable")
        return map_audiobook(card, self.instance_id)

    async def get_track(self, prov_track_id: str) -> Track:
        """Return one track by its stable provider ID."""
        track = self.catalogue.find_track(prov_track_id)
        if (
            track is None
            or (card := self.catalogue.cards.get(track.card_id)) is None
            or card.is_audiobook
        ):
            raise MediaNotFoundError("Yoto track is unavailable")
        return map_track(card, track, self.instance_id)

    async def get_album_tracks(self, prov_album_id: str) -> list[Track]:
        """Return the ordered tracks for one card."""
        if (card := self.catalogue.cards.get(prov_album_id)) is None or card.is_audiobook:
            raise MediaNotFoundError(f"Yoto card {prov_album_id!r} is unavailable")
        return [map_track(card, track, self.instance_id) for track in card.tracks]

    async def search(
        self, search_query: str, media_types: list[MediaType], limit: int = 5
    ) -> SearchResults:
        """Search cards, authors, series, chapters, and tracks."""
        needle = search_query.strip().casefold()
        result = SearchResults()
        if not needle or limit < 1:
            return result
        if MediaType.ALBUM in media_types:
            result.albums = [
                map_album(card, self.instance_id)
                for card in self.catalogue.cards.values()
                if not card.is_audiobook and needle in _card_search_text(card)
            ][:limit]
        if MediaType.AUDIOBOOK in media_types:
            result.audiobooks = [
                map_audiobook(card, self.instance_id)
                for card in self.catalogue.cards.values()
                if card.is_audiobook and needle in _card_search_text(card)
            ][:limit]
        if MediaType.TRACK in media_types:
            matches: list[Track] = []
            for card in self.catalogue.cards.values():
                if card.is_audiobook:
                    continue
                card_text = _card_search_text(card)
                for source in card.tracks:
                    track_text = (
                        f"{card_text} {source.chapter_title or ''} {source.title}".casefold()
                    )
                    if needle in track_text:
                        matches.append(map_track(card, source, self.instance_id))
                        if len(matches) >= limit:
                            break
                if len(matches) >= limit:
                    break
            result.tracks = matches
        return result

    async def browse(self, path: str) -> Sequence[Album | Audiobook | ItemMapping | BrowseFolder]:
        """Browse all cards and Yoto library groups."""
        root = f"{self.instance_id}://"
        if path in (self.instance_id, root):
            return [
                BrowseFolder(
                    item_id="cards",
                    provider=self.instance_id,
                    name="All Yoto cards",
                    path=f"{root}cards",
                ),
                BrowseFolder(
                    item_id="groups",
                    provider=self.instance_id,
                    name="Yoto library groups",
                    path=f"{root}groups",
                ),
            ]
        if path == f"{root}cards":
            return [_map_card(card, self.instance_id) for card in self.catalogue.cards.values()]
        if path == f"{root}groups":
            return [
                BrowseFolder(
                    item_id=group.item_id,
                    provider=self.instance_id,
                    name=group.name,
                    path=f"{root}group/{quote(group.item_id, safe='')}",
                    image=_image(group.artwork, self.instance_id) if group.artwork else None,
                )
                for group in self.catalogue.groups.values()
            ]
        prefix = f"{root}group/"
        if path.startswith(prefix):
            group = self.catalogue.groups.get(unquote(path.removeprefix(prefix)))
            if group is None:
                raise MediaNotFoundError("Yoto group is unavailable")
            return [
                _map_card(card, self.instance_id)
                for card_id in group.card_ids
                if (card := self.catalogue.cards.get(card_id)) is not None
            ]
        raise MediaNotFoundError("Unknown Yoto browse path")

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        """Resolve a fresh signed stream immediately before playback."""
        if media_type is MediaType.AUDIOBOOK:
            return await self._get_audiobook_stream_details(item_id)
        if media_type is not MediaType.TRACK:
            raise MediaNotFoundError("Yoto only streams tracks and audiobooks")
        source = self.catalogue.find_track(item_id)
        if (
            source is None
            or (card := self.catalogue.cards.get(source.card_id)) is None
            or card.is_audiobook
        ):
            raise MediaNotFoundError("Yoto track is unavailable")
        try:
            resolved = await self.adapter.resolve_stream(item_id)
        except ProviderUnavailableError as err:
            raise MediaNotFoundError(str(err)) from err
        return StreamDetails(
            provider=self.instance_id,
            item_id=item_id,
            audio_format=AudioFormat(content_type=_content_type(resolved.format or source.format)),
            media_type=MediaType.TRACK,
            stream_type=StreamType.HTTP,
            duration=resolved.duration or source.duration,
            path=resolved.path,
            allow_seek=True,
            can_seek=True,
        )

    async def _get_audiobook_stream_details(self, item_id: str) -> StreamDetails:
        """Build a multipart audiobook with short-lived capability URLs."""
        card = self.catalogue.cards.get(item_id)
        if card is None or not card.is_audiobook or not card.tracks:
            raise MediaNotFoundError("Yoto audiobook is unavailable")
        if not _has_compatible_formats(card):
            raise MediaNotFoundError("Yoto audiobook has incompatible audio properties")
        now = monotonic()
        sessions = self._get_audiobook_sessions()
        self._prune_audiobook_sessions(now)
        if len(sessions) >= MAX_PLAYBACK_SESSIONS:
            sessions.pop(next(iter(sessions)))
        session_id = secrets.token_urlsafe(32)
        duration = sum(max(source.duration, 0) for source in card.tracks)
        session_ttl = max(MIN_PLAYBACK_SESSION_TTL, duration + PLAYBACK_SESSION_BUFFER)
        sessions[session_id] = _AudiobookPlaybackSession(
            card_id=card.item_id,
            part_ids=tuple(source.item_id for source in card.tracks),
            expires_at=now + session_ttl,
        )
        parts = [
            MultiPartPath(
                path=(
                    f"{self.mass.streams.base_url}/{self.instance_id}_yoto_part"
                    f"?session_id={session_id}&part={part_index}"
                ),
                duration=source.duration,
            )
            for part_index, source in enumerate(card.tracks)
        ]
        return StreamDetails(
            provider=self.instance_id,
            item_id=item_id,
            audio_format=AudioFormat(content_type=_content_type(_common_format(card))),
            media_type=MediaType.AUDIOBOOK,
            stream_type=StreamType.HTTP,
            duration=duration,
            path=parts[0].path if len(parts) == 1 else parts,
            allow_seek=True,
            can_seek=True,
        )

    async def _handle_audiobook_part_request(self, request: web.Request) -> web.Response:
        """Resolve one authorized audiobook part to a fresh signed Yoto URL."""
        session_id = request.query.get("session_id")
        part_value = request.query.get("part")
        if not session_id or part_value is None:
            raise web.HTTPBadRequest(text="Missing audiobook session or part")
        try:
            part_index = int(part_value)
        except ValueError as err:
            raise web.HTTPBadRequest(text="Invalid audiobook part") from err
        sessions = self._get_audiobook_sessions()
        session = sessions.get(session_id)
        if session is None:
            raise web.HTTPNotFound(text="Yoto audiobook session is unavailable")
        if session.expires_at <= monotonic():
            sessions.pop(session_id, None)
            raise web.HTTPGone(text="Yoto audiobook session expired")
        if part_index < 0 or part_index >= len(session.part_ids):
            raise web.HTTPNotFound(text="Yoto audiobook part is unavailable")
        item_id = session.part_ids[part_index]
        source = self.catalogue.find_track(item_id)
        if (
            source is None
            or (card := self.catalogue.cards.get(source.card_id)) is None
            or not card.is_audiobook
            or card.item_id != session.card_id
        ):
            raise web.HTTPNotFound(text="Yoto audiobook part is unavailable")
        try:
            resolved = await self.adapter.resolve_stream(item_id)
        except ProviderUnavailableError as err:
            raise web.HTTPNotFound(text="Yoto audiobook part is unavailable") from err
        raise web.HTTPFound(location=resolved.path)

    def _get_audiobook_sessions(self) -> dict[str, _AudiobookPlaybackSession]:
        if not hasattr(self, "_audiobook_sessions"):
            self._audiobook_sessions = {}
        return self._audiobook_sessions

    def _prune_audiobook_sessions(self, now: float) -> None:
        sessions = self._get_audiobook_sessions()
        for session_id, session in tuple(sessions.items()):
            if session.expires_at <= now:
                sessions.pop(session_id, None)


def map_album(card: CatalogueCard, instance_id: str) -> Album:
    """Map a catalogue card to a Music Assistant album."""
    artist = _artist(card.author, instance_id)
    album = Album(
        item_id=card.item_id,
        provider=instance_id,
        name=card.title,
        artists=UniqueList([artist]),
        provider_mappings={_mapping(card.item_id, instance_id)},
    )
    album.metadata.description = card.description
    album.metadata.grouping = card.series_title
    if card.artwork:
        album.metadata.images = UniqueList([_image(card.artwork, instance_id)])
    return album


def map_audiobook(card: CatalogueCard, instance_id: str) -> Audiobook:
    """Map a story card to one resumable Music Assistant audiobook."""
    duration = sum(max(track.duration, 0) for track in card.tracks)
    is_playable = bool(card.tracks) and duration > 0 and _has_compatible_formats(card)
    audiobook = Audiobook(
        item_id=card.item_id,
        provider=instance_id,
        name=card.title,
        authors=UniqueList([card.author] if card.author else []),
        duration=duration,
        position=card.series_order,
        provider_mappings={
            _mapping(
                card.item_id,
                instance_id,
                _common_format(card),
                available=is_playable,
            )
        },
        is_playable=is_playable,
    )
    audiobook.metadata.description = card.description
    audiobook.metadata.grouping = card.series_title
    if card.category:
        audiobook.metadata.genres = {card.category}
    if card.artwork:
        audiobook.metadata.images = UniqueList([_image(card.artwork, instance_id)])
    elapsed = 0
    chapter_starts: list[tuple[str, str, int]] = []
    for track in card.tracks:
        if not chapter_starts or chapter_starts[-1][0] != track.chapter_key:
            chapter_starts.append((track.chapter_key, track.chapter_title or track.title, elapsed))
        elapsed += max(track.duration, 0)
    audiobook.metadata.chapters = [
        MediaItemChapter(
            position=index + 1,
            name=name,
            start=start,
            end=chapter_starts[index + 1][2] if index + 1 < len(chapter_starts) else elapsed,
        )
        for index, (_, name, start) in enumerate(chapter_starts)
    ]
    return audiobook


def map_track(card: CatalogueCard, source: CatalogueTrack, instance_id: str) -> Track:
    """Map a catalogue track to a Music Assistant track."""
    artist = _artist(card.author, instance_id)
    album = ItemMapping(
        item_id=card.item_id,
        provider=instance_id,
        name=card.title,
        media_type=MediaType.ALBUM,
        image=_image(card.artwork, instance_id) if card.artwork else None,
    )
    track = Track(
        item_id=source.item_id,
        provider=instance_id,
        name=source.title,
        duration=source.duration,
        artists=UniqueList([artist]),
        album=album,
        disc_number=1,
        track_number=source.track_number,
        provider_mappings={
            _mapping(source.item_id, instance_id, source.format, available=source.duration > 0)
        },
        is_playable=source.duration > 0,
    )
    artwork = source.artwork or card.artwork
    if artwork:
        track.metadata.images = UniqueList([_image(artwork, instance_id)])
    return track


def _card_search_text(card: CatalogueCard) -> str:
    return " ".join(
        value for value in (card.title, card.author, card.series_title, card.category) if value
    ).casefold()


def _map_card(card: CatalogueCard, instance_id: str) -> Album | Audiobook:
    return map_audiobook(card, instance_id) if card.is_audiobook else map_album(card, instance_id)


def _common_format(card: CatalogueCard) -> str | None:
    formats = {_normalize_stream_property(track.format) for track in card.tracks}
    formats.discard(None)
    return formats.pop() if len(formats) == 1 else None


def _has_compatible_formats(card: CatalogueCard) -> bool:
    formats = [_normalize_stream_property(track.format) for track in card.tracks]
    channels = [_normalize_stream_property(track.channels) for track in card.tracks]
    return (
        bool(formats)
        and all(value in {"aac", "mp3", "m4a", "mp4a"} for value in formats)
        and len(set(formats)) == 1
        and all(value in {"mono", "stereo"} for value in channels)
        and len(set(channels)) == 1
    )


def _normalize_stream_property(value: str | None) -> str | None:
    return value.strip().casefold() if value and value.strip() else None


def _artist(name: str | None, instance_id: str) -> Artist:
    artist_name = name or "Yoto"
    return Artist(
        item_id=f"author:{artist_name.casefold()}",
        provider=instance_id,
        name=artist_name,
        provider_mappings={_mapping(f"author:{artist_name.casefold()}", instance_id)},
    )


def _mapping(
    item_id: str,
    instance_id: str,
    content_format: str | None = None,
    *,
    available: bool = True,
) -> ProviderMapping:
    return ProviderMapping(
        item_id=item_id,
        provider_domain="yoto",
        provider_instance=instance_id,
        available=available,
        audio_format=AudioFormat(content_type=_content_type(content_format)),
    )


def _content_type(content_format: str | None) -> ContentType:
    return {
        "aac": ContentType.AAC,
        "mp3": ContentType.MP3,
        "m4a": ContentType.M4A,
        "mp4a": ContentType.MP4A,
    }.get((content_format or "").lower(), ContentType.UNKNOWN)


def _image(path: str, instance_id: str) -> MediaItemImage:
    return MediaItemImage(
        type=ImageType.THUMB,
        path=path,
        provider=instance_id,
        remotely_accessible=path.startswith(("http://", "https://")),
    )
