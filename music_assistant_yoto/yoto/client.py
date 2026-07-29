"""Authentication and API boundary for the Yoto provider."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from music_assistant_models.errors import LoginFailed, ProviderUnavailableError
from yoto_api import YotoClient

from .catalogue import Catalogue, decode_track_id

TokenCallback = Callable[[str], None | Awaitable[None]]


class YotoClientProtocol(Protocol):
    """Subset of yoto-api used by the provider."""

    token: Any
    library: dict[str, Any]
    groups: dict[str, Any]

    def set_refresh_token(self, refresh_token: str) -> None: ...

    async def device_code_flow_start(self) -> dict[str, Any]: ...

    async def device_code_flow_complete(self, auth_result: dict[str, Any]) -> Any: ...

    async def check_and_refresh_token(self) -> Any: ...

    async def update_library(self) -> None: ...

    async def update_card_detail(self, card_id: str) -> None: ...

    async def update_groups(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DeviceAuthEvent:
    """Browser URL and opaque state for an active device authorization."""

    url: str
    session: dict[str, Any] = field(repr=False)


@dataclass(frozen=True, slots=True)
class ResolvedStream:
    """A fresh stream URL kept out of representations and catalogue records."""

    path: str = field(repr=False)
    duration: int = 0
    format: str | None = None


class YotoAdapter:
    """Secret-safe adapter around yoto-api."""

    def __init__(
        self,
        client_id: str,
        refresh_token: str | None = None,
        *,
        api: YotoClientProtocol | None = None,
        token_callback: TokenCallback | None = None,
        session: Any = None,
    ) -> None:
        if not client_id.strip():
            raise LoginFailed("A Yoto client ID is required")
        self._api = api or YotoClient(client_id=client_id, session=session)
        self._token_callback = token_callback
        self._refresh_token = refresh_token
        if refresh_token:
            self._api.set_refresh_token(refresh_token)

    def __repr__(self) -> str:
        """Return a representation that never contains credentials."""
        return f"{type(self).__name__}(authenticated={bool(self._refresh_token)})"

    async def start_device_auth(self) -> DeviceAuthEvent:
        """Start device authorization and return the browser event URL."""
        try:
            auth_result = await self._api.device_code_flow_start()
            url = auth_result.get("verification_uri_complete") or auth_result.get(
                "verification_uri"
            )
            if not isinstance(url, str) or not url:
                raise LoginFailed("Yoto authorization did not return a browser URL")
            return DeviceAuthEvent(url=url, session=auth_result)
        except LoginFailed:
            raise
        except Exception as err:
            raise LoginFailed("Yoto device authorization failed") from err

    async def complete_device_auth(self, auth_session: Mapping[str, Any] | None) -> str:
        """Complete device authorization and persist its refresh token."""
        if not auth_session or "device_code" not in auth_session:
            raise LoginFailed("Yoto authorization session is missing")
        try:
            token = await self._api.device_code_flow_complete(
                auth_session if isinstance(auth_session, dict) else dict(auth_session)
            )
            refresh_token = getattr(token, "refresh_token", None)
            if not isinstance(refresh_token, str) or not refresh_token:
                raise LoginFailed("Yoto authorization returned no refresh token")
            await self._persist_token(refresh_token)
            return refresh_token
        except LoginFailed:
            raise
        except Exception as err:
            raise LoginFailed("Yoto device authorization failed") from err

    async def ensure_authenticated(self) -> None:
        """Refresh access before API use and persist token rotation."""
        if not self._refresh_token:
            raise LoginFailed("Yoto is not authenticated")
        try:
            token = await self._api.check_and_refresh_token()
            refresh_token = getattr(token, "refresh_token", None)
            if isinstance(refresh_token, str) and refresh_token != self._refresh_token:
                await self._persist_token(refresh_token)
        except LoginFailed:
            raise
        except Exception as err:
            raise LoginFailed("Yoto authentication failed") from err

    async def refresh_catalogue(self) -> Catalogue:
        """Fetch all cards, details, and groups into a URL-free snapshot."""
        await self.ensure_authenticated()
        try:
            await self._api.update_library()
            for card_id in tuple(self._api.library):
                await self._api.update_card_detail(card_id)
            await self._api.update_groups()
            return Catalogue.from_yoto_models(self._api.library, self._api.groups)
        except Exception as err:
            raise ProviderUnavailableError("Unable to refresh the Yoto library") from err

    async def resolve_stream(self, item_id: str) -> ResolvedStream:
        """Refetch one card and return its current signed stream."""
        try:
            card_id, chapter_key, track_key = decode_track_id(item_id)
        except ValueError as err:
            raise ProviderUnavailableError("Invalid Yoto track identifier") from err
        await self.ensure_authenticated()
        try:
            await self._api.update_card_detail(card_id)
            card = self._api.library[card_id]
            track = card.chapters[chapter_key].tracks[track_key]
            path = track.trackUrl
            if not isinstance(path, str) or not path.startswith("https://"):
                raise ProviderUnavailableError("Yoto stream is unavailable")
            return ResolvedStream(
                path=path,
                duration=track.duration or 0,
                format=track.format,
            )
        except ProviderUnavailableError:
            raise
        except Exception as err:
            raise ProviderUnavailableError("Yoto stream is unavailable") from err

    async def _persist_token(self, refresh_token: str) -> None:
        self._refresh_token = refresh_token
        if self._token_callback is not None:
            result = self._token_callback(refresh_token)
            if inspect.isawaitable(result):
                await result
