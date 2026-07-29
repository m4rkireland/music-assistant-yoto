# Upstream assessment

## Conclusion

A Yoto provider is technically compatible with Music Assistant's music-provider model, but this implementation should remain private/experimental until the authentication and API-policy risks below are resolved. Upstream acceptance is desirable but is not required for a working private provider.

## Positive fit

- Music Assistant already supports unofficial-provider warnings and OAuth-style setup actions.
- Cards map cleanly to albums and ordered playable items to tracks.
- The implementation is read-only, async, dependency-pinned, and tested against the exact 2.9.9 interfaces.
- `yoto-api` is MIT licensed, supports Python 3.14 in this verified environment, and has a pinned 4.3.2 release.

## Upstream gaps

1. **Authentication UX:** Browser PKCE is implemented, avoiding Yoto's deprecated device-code grant. A PR should replace the private callback-copy step with a polished loopback or registered HTTPS callback and document redirect-URI registration.
2. **API status:** `yoto-api` uses family-library and per-card endpoints that are not all represented in Yoto's current public reference. Maintainers may reject a provider based on private/unstable endpoints or content-rights concerns.
3. **Code ownership:** the manifest needs a real GitHub code owner committed to maintenance.
4. **Branding:** add reviewed `icon.svg` and `icon_monochrome.svg` within Music Assistant's size budgets.
5. **In-tree tests:** adapt the standalone tests to Music Assistant's `tests/providers/yoto/` conventions and run the full upstream pre-commit suite.
6. **Documentation URL:** replace the placeholder repository documentation URL with accepted Music Assistant documentation/discussion.
7. **Current development branch:** rebase the provider onto `dev`, not `stable`, and re-check model/API changes beyond 2.9.9.

## Contribution workflow and AI policy

- Open or identify a related issue/discussion before proposing a new provider.
- Target Music Assistant's `dev` branch and use its PR template and new-provider label/category.
- Run the repository setup, provider tests, manifest/icon checks, full pytest/pre-commit gates, and dependency review.
- Disclose that the implementation was AI-assisted and ensure a human contributor has reviewed, understands, can explain, test, and maintain every line. Do not submit generated code without that ownership.
- Never post or open a PR without explicit user approval.

## Sources

- Music Assistant 2.9.9 release: https://github.com/music-assistant/server/releases/tag/2.9.9
- Music Assistant provider development guide: https://github.com/music-assistant/server/blob/dev/DEVELOPMENT.md
- Music Assistant PR template: https://github.com/music-assistant/server/blob/dev/.github/PULL_REQUEST_TEMPLATE.md
- Music Assistant demo provider: https://github.com/music-assistant/server/tree/dev/music_assistant/providers/_demo_music_provider
- Yoto authentication overview: https://yoto.dev/authentication/auth/
- Yoto browser PKCE guide: https://yoto.dev/authentication/browser-auth/
- Yoto device-code migration notice: https://yoto.dev/authentication/device-code-migration/
- Yoto developer security/data policy: https://yoto.dev/get-started/data-privacy/
- `yoto-api` 4.3.2: https://github.com/cdnninja/yoto_api/tree/v4.3.2
