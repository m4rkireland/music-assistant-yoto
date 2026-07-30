# Changelog

## 2.9.9-yoto.9

- Present every non-audiobook Yoto card as one Music Assistant disc with its
  flattened Yoto audio entries as sequential tracks.

## 2.9.9-yoto.8

- Read the live `card.metadata.category` field so story and sleep cards are
  imported as native audiobooks with `yoto-api` 4.3.2.

## 2.9.9-yoto.7

- Represent Yoto story and sleep cards as native Music Assistant audiobooks.
- Preserve Yoto chapter boundaries on a seekable multipart timeline.
- Use Music Assistant's local resume and completion state.
- Resolve every audiobook part to a fresh signed URL only when that part starts.
- Keep music and unclassified cards as albums with ordered tracks.
- Use short-lived, audiobook-scoped capability URLs for fresh per-part stream resolution.
- Serialize simultaneous album, track, and audiobook syncs around one shared catalogue refresh.
- Mark unknown or incompatible multipart stream properties unavailable instead of risking corrupt concatenated playback.

## 2.9.9-yoto.6

- Restore the established album-and-track model for every Yoto card.
- Document native audiobook and resume semantics as potential future enhancements.
- Replace development-history documents with concise installation and security references.
- Remove environment-specific and speculative project notes.

## 2.9.9-yoto.5

- Map story and sleep cards to seekable Music Assistant audiobooks.
- Preserve ordered Yoto audio parts as an audiobook chapter timeline.
- Use Music Assistant's local playlog for audiobook resume positions.
- Keep music and unclassified cards as albums with ordered tracks.
- Rewrite public documentation and remove environment-specific development artifacts.

## 2.9.9-yoto.4

- Remove the unreliable browser-push authentication event.
- Present a selectable, mobile-friendly authorization URL with copy guidance
  and a direct native help link.

## 2.9.9-yoto.3

- Open the Yoto authorization page from the setup action using Music
  Assistant's native browser-auth event.
- Keep the generated URL visible as a copy/paste fallback.

## 2.9.9-yoto.2

- Flush single-use rotated Yoto refresh tokens to encrypted Music Assistant
  settings immediately so authentication survives a server restart.
- Show the generated authorization URL before the callback URL input.

## 2.9.9-yoto.1

- Base the custom app on the immutable Music Assistant Server 2.9.9 OCI image.
- Add the experimental, unofficial, read-only Yoto music provider.
- Pin `yoto-api` to 4.3.2.
- Support browser Authorization Code + PKCE authentication and secure refresh.
- Refresh the Yoto catalogue before Music Assistant library synchronization.
