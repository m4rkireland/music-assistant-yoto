# Music Assistant Yoto Provider

Experimental, unofficial, read-only Yoto music provider for **Music Assistant 2.9.9**.

It imports each Yoto card as an album and flattens chapters/tracks into deterministic playback order. Cards and tracks are searchable and browsable, including Yoto library groups. A card detail is fetched again immediately before playback so Music Assistant receives a fresh secure-media stream.

> This project is not affiliated with, supported by, or endorsed by Yoto. It relies on interfaces that may change without notice. Use may be subject to Yoto's terms and developer policies.

## Status

- Standalone provider artifact: implemented
- Automated unit/contract suite: implemented
- Music Assistant 2.9.9 discovery and setup screen: verified in an isolated instance
- Independent live Yoto authorization/account sync: verified
- Fresh real-account stream resolution and decoding: verified
- Sonos playback: deferred after isolated relay was blocked by inter-VLAN policy
- Production add-on: untouched

## Features

- Independent OAuth refresh token; no Home Assistant token dependency
- Browser-based Yoto Authorization Code + PKCE using the read-only library scope
- Rotating refresh-token persistence in a Music Assistant secure config field
- Cards as albums; playable chapter tracks as ordered tracks
- Card, track, chapter, author, category, and series search
- All-cards and Yoto-group browse views
- Automatic Yoto catalogue refresh before each Music Assistant library sync
- Artwork, duration, author, album association, and stable provider IDs
- Fresh stream URL resolution at playback time
- No signed URL in catalogue records, provider config, metadata, fixtures, or logs
- Read-only: no Yoto player, card, playlist, or account writes

## Development

```bash
uv python install 3.14
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
./scripts/check.sh
```

The default contract test uses `/home/dave/work/music-assistant-yoto-reference/server` at tag `2.9.9`; override with `MA_SERVER=/path/to/server`.

## Installation and rollback

See [docs/installation.md](docs/installation.md). The private installation method is deliberately reversible and does not overwrite a stock provider. Do not apply it to a production add-on until a deployment proposal has been reviewed and explicitly approved.

## Library synchronization

Music Assistant 2.9.9 schedules enabled provider library types every 12 hours. Before each Yoto album or track sync, the provider fetches a new family-library snapshot. Newly purchased and linked cards therefore appear automatically on the next scheduled sync. A manual Music Assistant provider/library sync makes them appear sooner; restarting the provider is not required.

Cards removed from the Yoto family library are marked as no longer present for the Yoto provider during a later sync. The provider never changes the Yoto account or cards.

## Limitations

- Yoto story cards are modelled as Music Assistant albums in this first version; audiobook resume semantics are future work.
- Browser PKCE uses the registered `http://localhost:8095/callback` redirect. Because Music Assistant runs on another host, the final localhost page normally fails to load and its complete callback URL must be copied back into the setup screen.
- Yoto's family-library and per-card endpoints used by `yoto-api` are not all represented in Yoto's current public API reference and may change.
- Signed streams are short-lived and must never be copied from debug tools or logs.
- Availability depends on the authenticated Yoto account and content rights.

## NFC / Tag Player

NFC is intentionally out of scope. When Music Assistant Tag Player is available, a later thin mapping can associate a scanned Yoto card UID with the already imported Music Assistant album or first track. See [docs/tag-player-future.md](docs/tag-player-future.md).
