# Yoto provider for Music Assistant

An experimental, unofficial, read-only provider that makes a family's Yoto card library available in [Music Assistant](https://music-assistant.io/).

> This project is not affiliated with, supported by, or endorsed by Yoto.

## Features

- Browser-based Yoto authentication using Authorization Code with PKCE
- No Yoto password or OAuth client secret required
- Cards represented as Music Assistant albums with ordered tracks
- Card artwork, titles, authors, series, chapters, durations, and library groups
- Search and browse support
- Automatic catalogue refresh during Music Assistant library synchronization
- Fresh signed media URLs resolved only when playback starts
- Encrypted refresh-token storage with immediate persistence after token rotation
- Read-only operation: the provider never changes the Yoto account or library

## Current media model

Every Yoto card is represented as a Music Assistant album. The card's playable content is exposed as ordered tracks; Yoto chapter order is preserved through disc and track numbering.

This compatibility model works for music and story cards without requiring changes to Music Assistant's media model. Native audiobook representation, chapter-aware resume positions, and audiobook completion state are not implemented. They are potential future enhancements.

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

Each synchronization refreshes the Yoto family library before importing albums and tracks. The provider does not use a webhook and changes are not immediate.

## Limitations

- The provider is experimental and tested against Music Assistant `2.9.9`.
- All cards currently use the album-and-track media model, including stories and other spoken-word content.
- Native audiobook resume and completion semantics are not available.
- Yoto's family-library and card-detail interfaces are not all covered by its public API reference and may change.
- The browser callback URL must currently be copied back into Music Assistant to complete authentication.

## Security

The provider is read-only. OAuth credentials are encrypted by Music Assistant, and short-lived signed media URLs are resolved only for playback rather than stored in the library.

See [Security](docs/security.md) for the complete data-handling model.
