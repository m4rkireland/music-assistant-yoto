"""Music Assistant mapping and provider implementation."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

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
    AudioFormat,
    BrowseFolder,
    ItemMapping,
    MediaItemImage,
    ProviderMapping,
    SearchResults,
    Track,
    UniqueList,
)
from music_assistant_models.streamdetails import StreamDetails

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
    ProviderFeature.LIBRARY_TRACKS,
}


class YotoProvider(MusicProvider):
    """Read-only Yoto card library provider."""

    adapter: YotoAdapter

    def __init__(
        self, mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
    ) -> None:
        """Initialize an empty Yoto provider."""
        super().__init__(mass, manifest, config, SUPPORTED_FEATURES)
        self.catalogue = Catalogue()

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
            token_callback=lambda token: self._update_config_value(
                CONF_REFRESH_TOKEN, token, encrypted=True
            ),
        )
        self.catalogue = await self.adapter.refresh_catalogue()

    @property
    def is_streaming_provider(self) -> bool:
        """Return whether this provider resolves remote streams."""
        return True

    async def get_library_albums(self) -> AsyncGenerator[Album]:
        """Yield all cards as albums."""
        for card in self.catalogue.cards.values():
            yield map_album(card, self.instance_id)

    async def get_library_tracks(self) -> AsyncGenerator[Track]:
        """Yield every playable card track in source order."""
        for card in self.catalogue.cards.values():
            for track in card.tracks:
                yield map_track(card, track, self.instance_id)

    async def get_album(self, prov_album_id: str) -> Album:
        """Return one card as an album."""
        if (card := self.catalogue.cards.get(prov_album_id)) is None:
            raise MediaNotFoundError(f"Yoto card {prov_album_id!r} is unavailable")
        return map_album(card, self.instance_id)

    async def get_track(self, prov_track_id: str) -> Track:
        """Return one track by its stable provider ID."""
        track = self.catalogue.find_track(prov_track_id)
        if track is None or (card := self.catalogue.cards.get(track.card_id)) is None:
            raise MediaNotFoundError("Yoto track is unavailable")
        return map_track(card, track, self.instance_id)

    async def get_album_tracks(self, prov_album_id: str) -> list[Track]:
        """Return the ordered tracks for one card."""
        if (card := self.catalogue.cards.get(prov_album_id)) is None:
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
                if needle in _card_search_text(card)
            ][:limit]
        if MediaType.TRACK in media_types:
            matches: list[Track] = []
            for card in self.catalogue.cards.values():
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

    async def browse(self, path: str) -> Sequence[Album | ItemMapping | BrowseFolder]:
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
            return [map_album(card, self.instance_id) for card in self.catalogue.cards.values()]
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
                map_album(card, self.instance_id)
                for card_id in group.card_ids
                if (card := self.catalogue.cards.get(card_id)) is not None
            ]
        raise MediaNotFoundError("Unknown Yoto browse path")

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        """Resolve a fresh signed stream immediately before playback."""
        if media_type is not MediaType.TRACK:
            raise MediaNotFoundError("Yoto only streams tracks")
        source = self.catalogue.find_track(item_id)
        if source is None:
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
        disc_number=source.chapter_number,
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
