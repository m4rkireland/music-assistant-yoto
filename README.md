# Yoto provider for Music Assistant

An experimental, unofficial, read-only [Music Assistant](https://music-assistant.io/) provider for a family's Yoto card library.

The provider imports Yoto cards into Music Assistant, preserves card and chapter metadata, supports search and browse, and resolves fresh signed media URLs only when playback begins.

> This project is not affiliated with, supported by, or endorsed by Yoto. Yoto APIs and content availability may change without notice. Use is subject to Yoto's terms and your content rights.

## Features

- Browser-based Yoto OAuth using Authorization Code with PKCE
- No Yoto password, OAuth client secret, or Home Assistant credential dependency
- Encrypted refresh-token storage with immediate persistence after token rotation
- Read-only access to cards, groups, metadata, artwork, and audio
- Automatic catalogue refresh during Music Assistant library synchronization
- Search across cards, authors, series, categories, chapters, and track titles
- Browse views for all cards and Yoto library groups
- Fresh signed stream resolution at playback time
- Music cards represented as albums with ordered tracks
- Story and sleep cards represented as seekable audiobooks with chapters and Music Assistant resume positions

## Media mapping

| Yoto content | Music Assistant representation |
| --- | --- |
| Category `stories`, `story`, or `sleep` | One audiobook per card |
| Music and unclassified cards | Album with ordered tracks |
| Yoto chapter/track sequence on a story card | Audiobook chapter timeline |
| Yoto library group | Browse folder |

Audiobook progress is stored in Music Assistant's playlog. The provider remains read-only and does not write listening progress back to Yoto.

## Compatibility

- Music Assistant Server `2.9.9`
- Python `3.14`
- `yoto-api==4.3.2`
- Home Assistant architectures: `amd64`, `aarch64`

## Install the Home Assistant add-on

1. Back up Home Assistant and the existing Music Assistant application data.
2. Add this repository to the Home Assistant App Store:
   `https://github.com/m4rkireland/music-assistant-yoto`
3. Install **Music Assistant Yoto**.
4. Stop the stock Music Assistant add-on before starting this add-on. Both use host networking and the same ports.
5. Open the Music Assistant UI and add the **Yoto** music provider.

The custom add-on uses a separate slug and data directory, so the stock add-on remains available for rollback. See [Installation and rollback](docs/installation.md) for details.

## Configure Yoto

A Yoto OAuth client configured for browser PKCE is required. The provider requests only:

- `family:library:view`
- `offline_access`

In Music Assistant:

1. Add the **Yoto** music provider.
2. Enter the Yoto OAuth client ID.
3. Select **Generate copyable Yoto authorization URL**.
4. Open the URL using the adjacent help link, or tap and hold the URL field to copy it.
5. Complete authorization on Yoto's site.
6. The registered localhost callback may fail to load. Copy its complete URL from the browser address bar.
7. Paste the callback URL into Music Assistant and select **Verify Yoto callback**.
8. Save the provider.

The PKCE verifier stays in the server-side setup session. Refresh credentials are stored as an encrypted Music Assistant configuration value.

## Synchronization and playback

Music Assistant schedules provider library synchronization every 12 hours by default. A manual provider sync imports newly linked cards sooner.

At each sync, the provider refreshes the Yoto family library before importing albums, tracks, and audiobooks. Story cards previously imported as albums are retired from that representation and reimported as audiobooks.

Audiobook resume positions are maintained locally by Music Assistant. During playback, Music Assistant treats the ordered Yoto audio parts as one seekable timeline and resumes inside the correct part.

## Development

Clone the matching Music Assistant source into the repository-local development path:

```bash
git clone --depth 1 --branch 2.9.9 \
  https://github.com/music-assistant/server.git \
  .music-assistant-server

uv python install 3.14
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -e '.[dev]'

(
  cd .music-assistant-server
  ./scripts/setup.sh .venv-yoto-isolated
)
uv pip install \
  --python .music-assistant-server/.venv-yoto-isolated/bin/python \
  'yoto-api==4.3.2'

./scripts/check.sh
```

Set `MA_SERVER=/path/to/server` to use another exact `2.9.9` checkout.

## Security and limitations

- The provider is strictly read-only.
- Signed media URLs are not stored in catalogue objects, provider mappings, configuration, fixtures, or logs.
- Yoto's family-library and card-detail interfaces are not all covered by its public API reference and may change.
- The localhost callback must currently be copied back into Music Assistant after browser authorization.
- Category-based media classification depends on Yoto metadata. Unknown categories remain albums to avoid accidental conversion.

See [Security and data handling](docs/security.md).

## License

The provider source is licensed under the terms in [LICENSE](LICENSE), if present. Third-party components retain their own licenses.
