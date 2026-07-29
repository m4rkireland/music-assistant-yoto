"""Yoto music provider for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType
from music_assistant_models.errors import LoginFailed

from .client import YotoAdapter

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

CONF_CLIENT_ID = "client_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACTION_AUTH = "authenticate"
CONF_SESSION_ID = "session_id"


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize the Yoto provider."""
    from .provider import YotoProvider

    return YotoProvider(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return Music Assistant configuration entries."""
    del instance_id
    values = values if values is not None else {}
    if action == CONF_ACTION_AUTH:
        if mass is None:
            raise LoginFailed("Music Assistant session is unavailable")
        session_id = values.get(CONF_SESSION_ID)
        client_id = values.get(CONF_CLIENT_ID)
        if not session_id or not client_id:
            raise LoginFailed("A session and client ID are required for Yoto authorization")
        values[CONF_REFRESH_TOKEN] = await _perform_device_auth(
            mass, str(session_id), str(client_id)
        )

    return (
        ConfigEntry(
            key="warning",
            type=ConfigEntryType.ALERT,
            label="Unofficial provider: Yoto's private API may change without notice.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_CLIENT_ID,
            type=ConfigEntryType.STRING,
            label="Yoto OAuth client ID",
            description="Client ID supplied by the user; this provider embeds no credentials.",
        ),
        ConfigEntry(
            key=CONF_ACTION_AUTH,
            type=ConfigEntryType.ACTION,
            label="Authorize Yoto",
            action=CONF_ACTION_AUTH,
            action_label="Open Yoto authorization",
        ),
        ConfigEntry(
            key=CONF_REFRESH_TOKEN,
            type=ConfigEntryType.SECURE_STRING,
            label="Yoto refresh token",
            hidden=True,
            required=True,
        ),
    )


async def _perform_device_auth(mass: MusicAssistant, session_id: str, client_id: str) -> str:
    from music_assistant.helpers.auth import AuthenticationHelper

    adapter = YotoAdapter(client_id, session=mass.http_session)
    event = await adapter.start_device_auth()
    async with AuthenticationHelper(mass, session_id) as auth_helper:
        auth_helper.send_url(event.url)
        return await adapter.complete_device_auth(event.session)
