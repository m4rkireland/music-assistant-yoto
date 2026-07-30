# Yoto provider for Music Assistant

An experimental, unofficial, read-only provider that makes a family's Yoto card library available in [Music Assistant](https://music-assistant.io/).

> This project is not affiliated with, supported by, or endorsed by Yoto.

## Features

- Browser-based Yoto authentication using Authorization Code with PKCE
- No Yoto password or OAuth client secret required
- Story and sleep cards represented as Music Assistant audiobooks
- Yoto chapters represented as seekable audiobook chapters with local resume and completion state
- Music and unclassified cards represented as albums with ordered tracks
- Card artwork, titles, authors, series, chapters, durations, and library groups
- Search and browse support
- Automatic catalogue refresh during Music Assistant library synchronization
- Fresh signed media URLs resolved only when playback starts
- Encrypted refresh-token storage with immediate persistence after token rotation
- Read-only operation: the provider never changes the Yoto account or library

## Media model

Cards classified by Yoto as `story`, `stories`, or `sleep` are represented as Music Assistant audiobooks. Their ordered audio parts form one seekable timeline, while Yoto chapter boundaries and titles are preserved as audiobook chapters. Music Assistant stores resume positions and completion state in its local playlog; the provider does not write progress to Yoto.

Music and unclassified cards remain albums with ordered tracks. Unknown categories are not guessed as audiobooks.

## Compatibility

- Music Assistant Server `2.9.9`
- Python `3.14`
- `yoto-api==4.3.2`
- Home Assistant add-on architectures: `amd64` and `aarch64`

## Home Assistant installation

1. Add this URL as a custom repository in the Home Assistant App Store:

   ```text
   https://github.com/m4rkireland/music-assistant-yoto
   ```

2. Install **Music Assistant Yoto**.
3. Stop the stock Music Assistant add-on before starting Music Assistant Yoto. Both use the same host-network ports.
4. Open Music Assistant and add the **Yoto** provider.

See [Installation](docs/installation.md) for upgrades, uninstalling, existing Music Assistant installations, and development setup.

## Yoto authentication

A Yoto OAuth client configured for browser PKCE is required. The provider requests:

- `family:library:view`
- `offline_access`

To configure the provider:

1. Enter the Yoto OAuth client ID.
2. Select **Generate copyable Yoto authorization URL**.
3. Open the generated link or copy it from the URL field.
4. Authorize access on Yoto's website.
5. Copy the complete localhost callback URL from the browser address bar. The callback page itself does not need to load.
6. Paste the callback URL into Music Assistant.
7. Select **Verify Yoto callback**, then save the provider.

The PKCE verifier remains in the server-side setup session. Music Assistant stores the resulting refresh credential as an encrypted configuration value.

## Synchronization

Music Assistant synchronizes provider libraries every 12 hours by default. Run a manual Yoto provider synchronization to import newly linked cards sooner.

Each synchronization refreshes the Yoto family library before importing albums, tracks, and audiobooks. The provider does not use a webhook and changes are not immediate.

## Limitations

- The provider is experimental and tested against Music Assistant `2.9.9`.
- Media classification depends on Yoto's category metadata. Unknown categories remain albums.
- Audiobook parts must report the same normalized format and channel layout. Cards with missing or incompatible stream properties are shown but marked unavailable because Music Assistant 2.9.9 cannot safely concatenate them.
- Yoto's family-library and card-detail interfaces are not all covered by its public API reference and may change.
- The browser callback URL must currently be copied back into Music Assistant to complete authentication.

## Security

The provider is read-only. OAuth credentials are encrypted by Music Assistant, and short-lived signed media URLs are resolved only for playback rather than stored in the library.

See [Security](docs/security.md) for the complete data-handling model.
