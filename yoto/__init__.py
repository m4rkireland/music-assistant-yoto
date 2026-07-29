"""Yoto provider setup and configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
from music_assistant_models.enums import ConfigEntryType, EventType

from .pkce import build_authorization, exchange_code
from .provider import YotoProvider

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType, ProviderManifest

CONF_CLIENT_ID = "client_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_AUTH_COMPLETE = "auth_complete"
CONF_ACTION_AUTH = "authenticate"
CONF_ACTION_VERIFY = "verify_callback"
CONF_AUTH_URL = "authorization_url"
CONF_CALLBACK_URL = "callback_url"
CONF_PKCE_PENDING = "pkce_pending"
REDIRECT_URI = "http://localhost:8095/callback"
_PKCE_SESSIONS: dict[str, str] = {}


async def setup(
    mass: MusicAssistant,
    manifest: ProviderManifest,
    config: ProviderConfig,
) -> ProviderInstanceType:
    """Set up the Yoto provider."""
    return YotoProvider(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant | None,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return provider configuration and handle PKCE browser authorization actions."""
    del instance_id
    values = values or {}
    client_id = str(values.get(CONF_CLIENT_ID) or "").strip()

    if action == CONF_ACTION_AUTH:
        if mass is None:
            raise RuntimeError("Music Assistant is required for Yoto authorization")
        authorization = build_authorization(client_id, REDIRECT_URI)
        session_id = str(values.get("session_id") or "")
        if not session_id:
            raise RuntimeError("Music Assistant authorization session is missing")
        if len(_PKCE_SESSIONS) >= 32:
            _PKCE_SESSIONS.pop(next(iter(_PKCE_SESSIONS)))
        _PKCE_SESSIONS[session_id] = authorization.verifier
        values[CONF_PKCE_PENDING] = True
        values[CONF_AUTH_URL] = authorization.url
        values[CONF_CALLBACK_URL] = ""
        values[CONF_AUTH_COMPLETE] = False
        mass.signal_event(EventType.AUTH_SESSION, session_id, authorization.url)

    if action == CONF_ACTION_VERIFY:
        if mass is None:
            raise RuntimeError("Music Assistant is required for Yoto authorization")
        session_id = str(values.get("session_id") or "")
        verifier = _PKCE_SESSIONS.get(session_id, "")
        callback_url = str(values.get(CONF_CALLBACK_URL) or "")
        if not verifier:
            raise RuntimeError("Start Yoto authorization before verifying the callback")
        token = await exchange_code(
            mass.http_session,
            client_id,
            REDIRECT_URI,
            verifier,
            callback_url,
        )
        values[CONF_REFRESH_TOKEN] = token.refresh_token
        values[CONF_AUTH_COMPLETE] = True
        values[CONF_PKCE_PENDING] = False
        values[CONF_AUTH_URL] = ""
        values[CONF_CALLBACK_URL] = ""
        _PKCE_SESSIONS.pop(session_id, None)

    pending_callback = bool(values.get(CONF_PKCE_PENDING))
    authenticated = bool(values.get(CONF_REFRESH_TOKEN)) or bool(values.get(CONF_AUTH_COMPLETE))

    return (
        ConfigEntry(
            key="warning",
            type=ConfigEntryType.ALERT,
            label=(
                "This is an unofficial integration that is not affiliated with Yoto, is not "
                "supported by Yoto, and is not endorsed by Yoto. It relies on private interfaces "
                "that may change without notice and use may be subject to Yoto's terms."
            ),
            required=False,
        ),
        ConfigEntry(
            key=CONF_CLIENT_ID,
            type=ConfigEntryType.STRING,
            label="Yoto OAuth client ID",
            required=True,
            value=values.get(CONF_CLIENT_ID),
        ),
        ConfigEntry(
            key="pkce_instructions",
            type=ConfigEntryType.ALERT,
            label=(
                "Open Yoto authorization and sign in on Yoto's site. The final localhost page "
                "will normally fail to load; copy its complete URL from the browser address bar, "
                "paste it below, then verify."
            ),
            required=False,
            hidden=not pending_callback,
        ),
        ConfigEntry(
            key=CONF_CALLBACK_URL,
            type=ConfigEntryType.STRING,
            label="Complete Yoto callback URL",
            description="It starts with http://localhost:8095/callback?code=",
            required=pending_callback,
            hidden=not pending_callback,
            value=values.get(CONF_CALLBACK_URL),
        ),
        ConfigEntry(
            key=CONF_AUTH_URL,
            type=ConfigEntryType.STRING,
            label="Yoto authorization URL",
            description="Open this URL if the authorization window did not appear.",
            required=False,
            hidden=not pending_callback,
            read_only=True,
            value=values.get(CONF_AUTH_URL),
        ),
        ConfigEntry(
            key=CONF_ACTION_VERIFY,
            type=ConfigEntryType.ACTION,
            label="Verify Yoto callback",
            action=CONF_ACTION_VERIFY,
            required=False,
            hidden=not pending_callback,
        ),
        ConfigEntry(
            key=CONF_ACTION_AUTH,
            type=ConfigEntryType.ACTION,
            label="Reauthorize Yoto" if authenticated else "Open Yoto authorization",
            action=CONF_ACTION_AUTH,
            required=False,
        ),
        ConfigEntry(
            key=CONF_PKCE_PENDING,
            type=ConfigEntryType.BOOLEAN,
            label="Yoto browser authorization pending",
            required=False,
            hidden=True,
            value=pending_callback,
        ),
        ConfigEntry(
            key=CONF_REFRESH_TOKEN,
            type=ConfigEntryType.SECURE_STRING,
            label="Yoto refresh token",
            required=True,
            hidden=True,
            value=values.get(CONF_REFRESH_TOKEN),
        ),
        ConfigEntry(
            key=CONF_AUTH_COMPLETE,
            type=ConfigEntryType.BOOLEAN,
            label="Yoto authorization complete",
            required=False,
            hidden=True,
            value=authenticated,
        ),
    )
