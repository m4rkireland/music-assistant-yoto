import json
from pathlib import Path

import pytest
from yoto_api import Card, Chapter, Group, Track

from yoto.catalogue import Catalogue, decode_track_id, encode_track_id

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_catalogue_preserves_card_chapter_track_order_with_reversible_ids() -> None:
    catalogue = Catalogue.from_responses(
        load("library.json"), {"card-alpha": load("card_detail.json")}
    )

    assert list(catalogue.cards) == ["card-alpha", "card-beta"]
    card = catalogue.cards["card-alpha"]
    assert card.title == "Moshi Moon"
    assert card.author == "Dream Reader"
    assert [track.title for track in card.tracks] == ["Second", "Third", "First"]
    assert [(track.chapter_number, track.track_number) for track in card.tracks] == [
        (1, 1),
        (1, 2),
        (2, 3),
    ]
    track_id = encode_track_id("card-alpha", "chapter-b", "track-z")
    assert decode_track_id(track_id) == ("card-alpha", "chapter-b", "track-z")
    assert card.tracks[0].item_id == track_id
    assert "stream" not in repr(catalogue).lower()


def test_catalogue_handles_missing_values_and_excludes_ephemeral_urls() -> None:
    catalogue = Catalogue.from_responses(
        load("library.json"), {"card-alpha": load("card_detail.json")}
    )

    assert catalogue.cards["card-beta"].title == "Rain Songs"
    assert catalogue.cards["card-beta"].tracks == ()
    assert not hasattr(catalogue.cards["card-alpha"].tracks[0], "track_url")
    assert "fixture-signed-stream-never-store" not in repr(catalogue)


@pytest.mark.parametrize("item_id", ["not-base64!", "W10", encode_track_id("a", "b", "c")[:-1]])
def test_decode_track_id_rejects_malformed_ids(item_id: str) -> None:
    with pytest.raises(ValueError, match="Invalid Yoto track ID"):
        decode_track_id(item_id)


def test_catalogue_rejects_malformed_library_response() -> None:
    with pytest.raises(ValueError, match="cards list"):
        Catalogue.from_responses({}, {})


def test_catalogue_from_yoto_models_preserves_metadata_and_drops_stream_url() -> None:
    track = Track(
        key="track-a",
        title="Moshi Track",
        duration=12,
        format="aac",
        trackUrl="https://secure-media.example/file?signature=fixture",
    )
    chapter = Chapter(key="chapter-a", title="Sleep", tracks={"track-a": track})
    card = Card(
        id="card-a",
        title="Moshi",
        author="Dream Reader",
        cover_image_large="fixture-art",
        series_title="Moshi Series",
        chapters={"chapter-a": chapter},
    )
    group = Group(id="sleep", name="Sleep", card_ids=["card-a"])

    catalogue = Catalogue.from_yoto_models({"card-a": card}, {"sleep": group})

    assert catalogue.cards["card-a"].series_title == "Moshi Series"
    assert catalogue.cards["card-a"].tracks[0].chapter_title == "Sleep"
    assert catalogue.groups["sleep"].card_ids == ("card-a",)
    assert "signature=" not in repr(catalogue)
