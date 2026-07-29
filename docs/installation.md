# Installation

## Requirements

- Home Assistant OS or a supervised Home Assistant installation
- Music Assistant Server `2.9.9`
- A Yoto OAuth client configured for Authorization Code with PKCE
- A Yoto account with access to the family library

## Install the Home Assistant add-on

1. Open **Settings → Apps → App store** in Home Assistant.
2. Add the following custom repository:

   ```text
   https://github.com/m4rkireland/music-assistant-yoto
   ```

3. Install **Music Assistant Yoto**.
4. Stop the stock Music Assistant add-on if it is installed.
5. Start Music Assistant Yoto and open its web interface.
6. Complete Music Assistant onboarding if this is a new installation.
7. Add the **Yoto** provider and follow the authentication steps in the [README](../README.md#yoto-authentication).

The stock and Yoto add-ons have different slugs and separate application-data directories. They must not run simultaneously because both use host networking and the same ports.

## Existing Music Assistant installation

Music Assistant Yoto can be configured as a new server, or it can use a migrated copy of an existing Music Assistant data directory.

Before migrating an existing installation:

1. Create a Home Assistant backup.
2. Stop both Music Assistant add-ons.
3. Preserve the original stock add-on data.
4. Copy the Music Assistant application data to the Yoto add-on's data directory using a method appropriate for the Home Assistant installation.
5. Start only Music Assistant Yoto.
6. Verify existing providers, players, and library content before removing any backup.

Application-data paths are managed by Home Assistant Supervisor and vary by installation. Direct data migration is an advanced operation; a fresh Music Assistant configuration is the safer default.

## Upgrade

1. Review the add-on changelog.
2. Create a Home Assistant backup.
3. Refresh the custom repository in the App Store.
4. Install the available update.
5. Confirm Music Assistant reaches the `running` state and the Yoto provider loads.
6. Run a manual Yoto synchronization when a release changes catalogue mapping.

## Return to stock Music Assistant

1. Stop Music Assistant Yoto.
2. Disable its automatic start and watchdog.
3. Restore or retain the stock Music Assistant application data.
4. Start the stock Music Assistant add-on.
5. Confirm that only one Music Assistant server is running.

## Uninstall

1. Stop Music Assistant Yoto.
2. Confirm that any required Music Assistant configuration has been backed up.
3. Uninstall the add-on.
4. Remove the custom repository from the Home Assistant App Store if it is no longer needed.

Uninstalling the add-on does not revoke Yoto authorization. Remove the Yoto provider or revoke the authorization separately if access should be withdrawn.

## Development setup

Clone the matching Music Assistant source into `.music-assistant-server` at the repository root:

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

Set `MA_SERVER` to use another exact Music Assistant `2.9.9` checkout.

For an isolated server checkout, install or remove the provider symlink with:

```bash
./scripts/install-isolated.sh
./scripts/remove-isolated.sh
```
