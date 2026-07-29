# Security and data handling

## Secrets

- The user supplies a Yoto developer OAuth client ID; no client secret or Yoto password is requested.
- The refresh token is stored in a Music Assistant `SECURE_STRING` config entry.
- Refresh tokens are single-use and rotated. The replacement token is persisted immediately after refresh.
- Access tokens, refresh tokens, PKCE verifiers, authorization codes, and signed stream URLs are excluded from provider-model representations and sanitized exception messages.
- PKCE verifiers remain server-side in short-lived setup-session state and are never sent to the browser as configuration values.

## Signed media URLs

A signed URL is fetched only when `get_stream_details` is called. It is returned internally to Music Assistant for playback but is never put in an album/track object, provider mapping, catalogue snapshot, configuration field, fixture, diagnostic, or log message. Debugging must report only non-secret facts such as host, content type, and HTTP status.

## Read-only scope

The provider calls library, group, card-detail, OAuth, and refresh operations only. It does not connect to Yoto MQTT, control Yoto players, or call card/account/device write operations.

## External-policy risks

- The private family-library/card endpoints may change and are not all in Yoto's current public API reference.
- The provider uses Yoto's currently recommended browser PKCE flow. Its localhost callback-copy UX is suitable for private setup but should be replaced with a polished loopback or registered HTTPS callback before upstream submission.
- Users remain responsible for Yoto terms, account permissions, and content rights.

## Incident response

If a signed URL or OAuth token is ever logged: stop the test instance, delete the affected logs, revoke/rotate the Yoto authorization, remove the provider config, and reauthorize. Treat refresh-token persistence failures as authentication failures; do not retry using an already-consumed old token indefinitely.
