# Installation, upgrade, and rollback

## Home Assistant installation

The repository contains a separate Home Assistant add-on that layers the Yoto provider onto the immutable Music Assistant Server `2.9.9` image.

1. Create a Home Assistant backup.
2. Add `https://github.com/m4rkireland/music-assistant-yoto` as a custom App Store repository.
3. Install **Music Assistant Yoto**.
4. Stop the stock Music Assistant add-on before starting Music Assistant Yoto.
5. Start Music Assistant Yoto and open its web interface.
6. Configure the Yoto provider as described in the project README.

The custom add-on and stock add-on have different slugs and separate application-data directories. Do not run both simultaneously because both use host networking and the same Music Assistant ports.

## Existing Music Assistant installations

The safest default is a fresh Music Assistant Yoto configuration. To retain an existing Music Assistant library and provider configuration, migrate the application data while both add-ons are stopped, then start only Music Assistant Yoto.

Application-data migration is platform-specific. Always preserve the original stock add-on data and a Home Assistant backup until the new add-on has passed the validation checklist.

## Upgrade

1. Create a Home Assistant backup.
2. Refresh the custom repository in the App Store.
3. Review the add-on changelog.
4. Apply the available Music Assistant Yoto update.
5. Confirm the server reaches `running` state and the Yoto provider loads after restart.
6. Run a manual Yoto library synchronization when a release changes media mapping.

Source releases are immutable once published. Each provider update increments the add-on version.

## Rollback

### Roll back to an earlier Music Assistant Yoto version

1. Stop Music Assistant Yoto.
2. Restore the Home Assistant backup created before the update.
3. Start Music Assistant Yoto and verify providers and players.

### Return to stock Music Assistant

1. Stop Music Assistant Yoto and disable its watchdog/automatic start.
2. Restore or retain the stock Music Assistant application data.
3. Start the stock Music Assistant add-on.
4. Confirm only one Music Assistant server is running.

## Validation checklist

- Music Assistant reports server version `2.9.9` and status `running`.
- Only one Music Assistant add-on is running.
- Existing music and player providers load.
- Yoto loads without an authentication error after restart.
- Music cards appear under albums; story/sleep cards appear under audiobooks.
- Audiobook artwork, authors, chapters, duration, seeking, and resume position are correct.
- A manual synchronization discovers newly linked cards.
- Playback succeeds and no signed URL or OAuth credential appears in logs.

## Isolated development installation

```bash
git clone --depth 1 --branch 2.9.9 \
  https://github.com/music-assistant/server.git \
  .music-assistant-server

./scripts/install-isolated.sh
```

The script creates a reversible provider symlink only inside the exact `2.9.9` source checkout. Remove it with:

```bash
./scripts/remove-isolated.sh
```

Set `MA_SERVER=/path/to/server` or pass the source path as the first argument to either script.
