# Security and data handling

## Authentication

- The user supplies a Yoto OAuth client ID. No client secret, Yoto password, or Home Assistant credential is requested.
- Authorization uses the browser Authorization Code flow with PKCE.
- Requested scopes are limited to `family:library:view` and `offline_access`.
- The PKCE verifier and pending authorization state remain in the server-side setup session.
- Refresh tokens are stored in a Music Assistant `SECURE_STRING` configuration entry.
- Rotated refresh tokens are encrypted and flushed to configuration immediately.

## Signed media URLs

Yoto media URLs are short-lived credentials. The provider fetches them only while preparing playback.

Signed URLs are never added to:

- catalogue snapshots;
- albums, tracks, audiobooks, or chapter metadata;
- provider mappings;
- provider configuration;
- fixtures or documentation;
- application log messages.

For multi-part audiobooks, current URLs are resolved for the ordered audio parts at playback setup and passed directly to Music Assistant's stream pipeline.

## Resume positions

Audiobook progress is stored in Music Assistant's local playlog. The provider does not send progress, completion state, favorites, library edits, or playback commands to Yoto.

## Read-only API surface

The provider uses authentication, token refresh, family-library, card-detail, and library-group operations. It does not connect to Yoto MQTT, control Yoto players, or call account, device, card, playlist, or library mutation endpoints.

## Operational considerations

- Some family-library and card-detail interfaces used by `yoto-api` are not represented in Yoto's public API reference and may change.
- Content availability depends on the authenticated account and its rights.
- Unknown Yoto categories remain albums; only the recognized `stories`, `story`, and `sleep` values are mapped as audiobooks.
- Debug logs should report only non-secret information such as provider state, media type, host, content format, and HTTP status.

## Incident response

If an OAuth credential or signed media URL is exposed:

1. Stop the affected Music Assistant instance.
2. Remove the affected logs or diagnostics from shared storage.
3. Revoke the Yoto authorization.
4. Remove and reconfigure the Yoto provider.
5. Verify that the replacement refresh token persists across restart.
