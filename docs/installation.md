# Installation, upgrade, and rollback

## Supported private deployment shape

The provider must exist as a directory named `yoto` under the exact Music Assistant Python package's `music_assistant/providers/` directory. Music Assistant 2.9.9 has no stable external-provider plug-in directory, so a private production deployment will require a derived image or custom add-on that layers this directory onto the stock server image.

Do **not** patch a running stock add-on container: container changes are ephemeral, difficult to audit, and unsafe to roll back.

## Isolated 2.9.9 verification

```bash
git clone https://github.com/music-assistant/server.git /path/to/ma-server
cd /path/to/ma-server
git checkout 2.9.9
/path/to/music-assistant-yoto/scripts/install-isolated.sh /path/to/ma-server
./scripts/setup.sh .venv-yoto-isolated
uv pip install --python .venv-yoto-isolated/bin/python 'yoto-api==4.3.2'
PYTHONDEVMODE=1 .venv-yoto-isolated/bin/python -m music_assistant \
  --data-dir /path/to/isolated-data \
  --cache-dir /path/to/isolated-cache \
  --log-level debug
```

Open the isolated UI on port 8095, create a disposable local administrator, then open **Settings → Music sources → Add a music source → Yoto**. The setup page must show the unofficial warning, client-ID field, and authorization action.

Removal is reversible:

```bash
/path/to/music-assistant-yoto/scripts/remove-isolated.sh /path/to/ma-server
rm -rf /path/to/isolated-data /path/to/isolated-cache
```

## Proposed production method — not yet approved

1. Pin the stock Music Assistant server/add-on image corresponding to 2.9.9.
2. Build a derived image that copies only the reviewed `yoto/` directory into `music_assistant/providers/yoto/`.
3. Install `yoto-api==4.3.2` in the image, rather than at runtime.
4. Publish the image with an immutable version tag and digest.
5. Point a dedicated custom Home Assistant add-on repository/slug at that image; do not overwrite the stock add-on slug or data directory.
6. Back up the Music Assistant data directory before first start.
7. Validate provider discovery, existing provider/player inventory, Yoto authentication, library counts, search, and one explicitly approved playback.

No production image, add-on, config, or restart may be performed without Mark's explicit approval after reviewing the exact Dockerfile/add-on changes and image digest.

## Upgrade

- Build a new immutable derived-image tag from a reviewed provider commit.
- Run `scripts/check.sh` and repeat isolated discovery/account-sync verification.
- Stop the custom add-on, switch only its image tag, start it, and run the smoke checklist.
- Never mutate the old image tag.

## Rollback

1. Stop the custom add-on.
2. Restore its prior immutable image tag/digest.
3. Restore the pre-change Music Assistant data backup only if a schema/data migration occurred or validation shows corruption.
4. Start the previous image and verify existing music and player providers.
5. The stock add-on remains available because its slug/image was never overwritten.

## Smoke checklist

- Server reports expected version and reaches ready state.
- Existing production providers and players are unchanged.
- Yoto provider loads without errors.
- Expected card/track counts are present.
- `Moshi` returns the expected card and ordered tracks.
- A fresh stream resolves with no signed URL in logs.
- Only after separate approval: selected track plays on the specified Sonos with correct state and metadata.
