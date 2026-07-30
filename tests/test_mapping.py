import json
from dataclasses import replace
from pathlib import Path

from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.enums import ImageType, MediaType
from music_assistant_models.media_items import Album, Audiobook, Track

from yoto.catalogue import Catalogue
from yoto.provider import YotoProvider, map_album, map_audiobook, map_track

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def catalogue() -> Catalogue:
    return Catalogue.from_responses(load("library.json"), {"card-alpha": load("card_detail.json")})


def test_card_maps_to_album_with_author_artwork_and_stable_mapping() -> None:
    card = catalogue().cards["card-alpha"]

    album = map_album(card, "yoto-instance")

    assert isinstance(album, Album)
    assert album.item_id == "card-alpha"
    assert album.name == "Moshi Moon"
    assert album.artists[0].name == "Dream Reader"
    assert album.metadata.description == "Calm bedtime stories"
    assert album.metadata.images[0].type is ImageType.THUMB
    assert album.metadata.images[0].path == "fixture-artwork-card-alpha"
    mapping = next(iter(album.provider_mappings))
    assert mapping.item_id == "card-alpha"
    assert mapping.provider_domain == "yoto"
    assert mapping.provider_instance == "yoto-instance"
    assert mapping.url is None


def test_tracks_flatten_in_playback_order_with_album_and_author_fallback() -> None:
    snapshot = catalogue()
    card = snapshot.cards["card-beta"]
    fallback_album = map_album(card, "yoto-instance")
    assert fallback_album.artists[0].name == "Yoto"

    source = snapshot.cards["card-alpha"]
    tracks = [map_track(source, track, "yoto-instance") for track in source.tracks]

    assert all(isinstance(track, Track) for track in tracks)
    assert [track.name for track in tracks] == ["Second", "Third", "First"]
    assert [track.track_number for track in tracks] == [1, 2, 3]
    assert [track.disc_number for track in tracks] == [1, 1, 1]
    assert [track.duration for track in tracks] == [8, 7, 4]
    assert tracks[0].album.item_id == source.item_id
    assert tracks[0].media_type is MediaType.TRACK
    assert next(iter(tracks[0].provider_mappings)).url is None


def test_story_card_maps_to_one_resumable_audiobook_with_ordered_chapters() -> None:
    card = catalogue().cards["card-alpha"]

    audiobook = map_audiobook(card, "yoto-instance")

    assert isinstance(audiobook, Audiobook)
    assert audiobook.item_id == "card-alpha"
    assert audiobook.name == "Moshi Moon"
    assert audiobook.authors == ["Dream Reader"]
    assert audiobook.duration == 19
    assert audiobook.position == 2
    assert audiobook.metadata.grouping == "Moshi"
    assert audiobook.is_playable is False
    assert [
        (chapter.position, chapter.name, chapter.start, chapter.end)
        for chapter in audiobook.metadata.chapters or []
    ] == [
        (1, "Chapter Two", 0, 15),
        (2, "Chapter One", 15, 19),
    ]
    mapping = next(iter(audiobook.provider_mappings))
    assert mapping.item_id == "card-alpha"
    assert mapping.provider_domain == "yoto"
    assert mapping.url is None
    assert mapping.available is False


def test_audiobook_playability_requires_known_normalized_matching_stream_properties() -> None:
    card = catalogue().cards["card-alpha"]
    compatible = replace(
        card,
        tracks=tuple(replace(track, format=" AAC ", channels="Stereo") for track in card.tracks),
    )
    missing_format = replace(
        compatible,
        tracks=(replace(compatible.tracks[0], format=None), *compatible.tracks[1:]),
    )
    mixed_channels = replace(
        compatible,
        tracks=(replace(compatible.tracks[0], channels="mono"), *compatible.tracks[1:]),
    )
    unknown_format = replace(
        compatible,
        tracks=tuple(replace(track, format="banana") for track in compatible.tracks),
    )
    unknown_channels = replace(
        compatible,
        tracks=tuple(replace(track, channels="surround-ish") for track in compatible.tracks),
    )

    assert map_audiobook(compatible, "yoto-instance").is_playable is True
    assert map_audiobook(missing_format, "yoto-instance").is_playable is False
    assert map_audiobook(mixed_channels, "yoto-instance").is_playable is False
    assert map_audiobook(unknown_format, "yoto-instance").is_playable is False
    assert map_audiobook(unknown_channels, "yoto-instance").is_playable is False


def test_provider_uses_exact_music_assistant_base_contract() -> None:
    assert issubclass(YotoProvider, MusicProvider)
