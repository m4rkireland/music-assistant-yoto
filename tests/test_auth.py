from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from music_assistant_models.enums import ConfigEntryType
from music_assistant_models.errors import LoginFailed

from yoto import (
    CONF_ACTION_AUTH,
    CONF_ACTION_VERIFY,
    CONF_CALLBACK_URL,
    CONF_CLIENT_ID,
    CONF_PKCE_PENDING,
    CONF_REFRESH_TOKEN,
    get_config_entries,
)
from yoto.client import YotoAdapter


@dataclass
class FakeToken:
    refresh_token: str | None

    def __repr__(self) -> str:
        return "FakeToken(refresh_token=<redacted>)"


class FakeYotoClient:
    def __init__(self) -> None:
        self.token: FakeToken | None = None
        self.library: dict[str, Any] = {}
        self.groups: dict[str, Any] = {}
        self.calls: list[str] = []
        self.auth_result = {
            "device_code": "fixture-device-code",
            "verification_uri_complete": "fixture-browser-event-url",
        }

    def set_refresh_token(self, token: str) -> None:
        self.token = FakeToken(token)

    async def device_code_flow_start(self) -> dict[str, Any]:
        self.calls.append("start")
        return self.auth_result

    async def device_code_flow_complete(self, result: dict[str, Any]) -> FakeToken:
        self.calls.append("complete")
        assert result is self.auth_result
        self.token = FakeToken("fixture-initial-refresh")
        return self.token

    async def check_and_refresh_token(self) -> FakeToken:
        self.calls.append("refresh")
        self.token = FakeToken("fixture-rotated-refresh")
        return self.token


@pytest.mark.asyncio
async def test_config_schema_warns_and_keeps_refresh_token_secure() -> None:
    entries = await get_config_entries(None)
    by_key = {entry.key: entry for entry in entries}

    assert "unofficial" in by_key["warning"].label.lower()
    assert "not affiliated" in by_key["warning"].label.lower()
    assert "not endorsed" in by_key["warning"].label.lower()
    assert by_key[CONF_CLIENT_ID].required
    assert by_key[CONF_REFRESH_TOKEN].type is ConfigEntryType.SECURE_STRING
    assert by_key[CONF_REFRESH_TOKEN].hidden
    assert by_key[CONF_PKCE_PENDING].hidden
    assert by_key[CONF_ACTION_AUTH].action == CONF_ACTION_AUTH
    assert by_key[CONF_CALLBACK_URL].hidden
    assert by_key[CONF_ACTION_VERIFY].hidden


@pytest.mark.asyncio
async def test_pkce_start_exposes_browser_url_and_callback_step() -> None:
    events: list[tuple[Any, ...]] = []

    class FakeMass:
        def signal_event(self, *args: Any) -> None:
            events.append(args)

    values: dict[str, Any] = {
        CONF_CLIENT_ID: "fixture-client-id",
        "session_id": "fixture-session",
    }
    entries = await get_config_entries(FakeMass(), action=CONF_ACTION_AUTH, values=values)  # type: ignore[arg-type]
    by_key = {entry.key: entry for entry in entries}

    assert values[CONF_PKCE_PENDING]
    assert "fixture-client-id" in events[0][2]
    assert "family%3Alibrary%3Aview" in events[0][2]
    assert not by_key[CONF_CALLBACK_URL].hidden
    assert by_key[CONF_CALLBACK_URL].required
    assert not by_key[CONF_ACTION_VERIFY].hidden
    assert "fixture-verifier" not in repr(entries)


class FakeTokenResponse:
    ok = True

    async def __aenter__(self) -> FakeTokenResponse:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None

    async def json(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "access_token": "fixture-access",
            "refresh_token": "fixture-refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
        }


class FakeHttpSession:
    def post(self, *_args: Any, **_kwargs: Any) -> FakeTokenResponse:
        return FakeTokenResponse()


@pytest.mark.asyncio
async def test_pkce_callback_exchange_captures_refresh_token_securely() -> None:
    mass = type("FakeMass", (), {"http_session": FakeHttpSession()})()
    values: dict[str, Any] = {
        CONF_CLIENT_ID: "fixture-client-id",
        CONF_PKCE_PENDING: True,
        CONF_CALLBACK_URL: "http://localhost:8095/callback?code=fixture-code",
        "session_id": "fixture-session",
    }
    from yoto import _PKCE_SESSIONS

    _PKCE_SESSIONS["fixture-session"] = "fixture-verifier"

    entries = await get_config_entries(mass, action=CONF_ACTION_VERIFY, values=values)  # type: ignore[arg-type]
    by_key = {entry.key: entry for entry in entries}

    assert values[CONF_REFRESH_TOKEN] == "fixture-refresh"
    assert values[CONF_PKCE_PENDING] is False
    assert by_key[CONF_REFRESH_TOKEN].hidden
    assert by_key[CONF_REFRESH_TOKEN].type is ConfigEntryType.SECURE_STRING


@pytest.mark.asyncio
async def test_device_auth_exposes_browser_url_and_captures_token() -> None:
    fake = FakeYotoClient()
    saved: list[str] = []
    adapter = YotoAdapter("fixture-client-id", api=fake, token_callback=saved.append)

    event = await adapter.start_device_auth()
    token = await adapter.complete_device_auth(event.session)

    assert event.url == "fixture-browser-event-url"
    assert token == "fixture-initial-refresh"
    assert saved == ["fixture-initial-refresh"]
    assert "fixture-initial-refresh" not in repr(adapter)


@pytest.mark.asyncio
async def test_api_use_refreshes_first_and_persists_rotated_token() -> None:
    fake = FakeYotoClient()
    saved: list[str] = []
    adapter = YotoAdapter(
        "fixture-client-id",
        refresh_token="fixture-old-refresh",
        api=fake,
        token_callback=saved.append,
    )

    await adapter.ensure_authenticated()

    assert fake.calls == ["refresh"]
    assert saved == ["fixture-rotated-refresh"]


@pytest.mark.asyncio
async def test_missing_credentials_and_invalid_refresh_are_login_failures() -> None:
    with pytest.raises(LoginFailed, match="client ID"):
        YotoAdapter("")

    class BrokenClient(FakeYotoClient):
        async def check_and_refresh_token(self) -> FakeToken:
            raise RuntimeError("invalid refresh_token=fixture-secret")

    adapter = YotoAdapter("fixture-client-id", refresh_token="fixture-secret", api=BrokenClient())
    with pytest.raises(LoginFailed, match="authentication failed") as err:
        await adapter.ensure_authenticated()
    assert "fixture-secret" not in str(err.value)
