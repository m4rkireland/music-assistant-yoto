# Security

## Access model

The provider is read-only. It retrieves the authenticated family's Yoto library, card metadata, artwork, groups, and playback URLs. It does not:

- modify cards, playlists, groups, account settings, or devices;
- control Yoto players;
- publish listening progress or completion state to Yoto;
- connect to Yoto MQTT services;
- require Home Assistant credentials.

## OAuth authorization

Authorization uses the OAuth Authorization Code flow with PKCE. The configured OAuth client is treated as a public client, so no client secret is required.

Requested scopes:

- `family:library:view`
- `offline_access`

The PKCE verifier and pending authorization state remain in the Music Assistant setup session. The provider validates the returned state before exchanging the authorization code.

## Credential storage

The refresh token is stored in a Music Assistant `SECURE_STRING` configuration entry. Music Assistant encrypts secure configuration values at rest.

Yoto may rotate the refresh token during renewal. The provider writes a rotated token to encrypted configuration immediately and flushes the configuration before continuing.

The provider does not log:

- access or refresh tokens;
- authorization codes;
- callback URLs containing authorization codes;
- PKCE verifiers;
- OAuth client credentials.

## Media URLs

Yoto playback URLs are signed and time-limited. The provider resolves a fresh URL when Music Assistant prepares a track for playback.

Signed media URLs are not stored in:

- album or track metadata;
- provider mappings;
- provider configuration;
- test fixtures;
- application logs.

## Data retained by Music Assistant

Music Assistant stores imported catalogue metadata such as card titles, track titles, authors, artwork references, durations, and provider identifiers. Playback history and library state are managed by Music Assistant according to its own configuration.

The provider does not maintain a separate catalogue database.

## Revoking access

To withdraw access:

1. Remove or disable the Yoto provider in Music Assistant.
2. Revoke the authorization from the Yoto account or OAuth client management interface.
3. Remove logs or diagnostics if they were captured while debug logging was enabled.

Removing the Home Assistant add-on alone does not revoke the OAuth authorization.

## Reporting a vulnerability

Do not include credentials, authorization callbacks, signed media URLs, private library metadata, or diagnostic archives in a public issue.

Report the minimum reproducible details and redact all authentication material. If the issue could expose credentials or another user's data, contact the repository maintainer privately before opening a public report.

## Third-party interfaces

Some Yoto family-library and card-detail interfaces used by `yoto-api` are not represented in Yoto's public API reference. Their behavior may change independently of this project. Use the provider only with accounts and content you are authorized to access.
