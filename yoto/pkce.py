"""Yoto browser authorization using OAuth 2.0 Authorization Code + PKCE."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from music_assistant_models.errors import LoginFailed

AUTHORIZE_URL = "https://login.yotoplay.com/authorize"
TOKEN_URL = "https://login.yotoplay.com/oauth/token"
AUDIENCE = "https://api.yotoplay.com"
SCOPES = "family:library:view offline_access"


@dataclass(frozen=True, slots=True)
class PkceAuthorization:
    """Authorization URL plus its secret verifier."""

    url: str
    verifier: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class PkceToken:
    """Token response with secret fields excluded from representations."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int
    token_type: str = "Bearer"
    scope: str | None = None


def create_verifier() -> str:
    """Generate a high-entropy RFC 7636 verifier."""
    return secrets.token_urlsafe(64)


def build_authorization(
    client_id: str,
    redirect_uri: str,
    verifier: str | None = None,
) -> PkceAuthorization:
    """Build Yoto's browser authorization URL."""
    if not client_id.strip():
        raise LoginFailed("A Yoto client ID is required")
    verifier = verifier or create_verifier()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode()
    challenge = challenge.rstrip("=")
    query = urlencode(
        {
            "audience": AUDIENCE,
            "scope": SCOPES,
            "response_type": "code",
            "client_id": client_id,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "redirect_uri": redirect_uri,
        }
    )
    return PkceAuthorization(url=f"{AUTHORIZE_URL}?{query}", verifier=verifier)


def extract_authorization_code(callback_url: str, redirect_uri: str) -> str:
    """Validate a pasted callback URL and return its one-time code."""
    callback = urlsplit(callback_url.strip())
    expected = urlsplit(redirect_uri)
    callback_base = (callback.scheme, callback.netloc, callback.path)
    expected_base = (expected.scheme, expected.netloc, expected.path)
    if callback_base != expected_base:
        raise LoginFailed("Yoto callback URL does not match the registered redirect URL")
    query = parse_qs(callback.query)
    if error := query.get("error"):
        description = query.get("error_description", error)[0]
        raise LoginFailed(f"Yoto authorization was not completed: {description}")
    code = query.get("code", [""])[0]
    if not code:
        raise LoginFailed("Yoto callback URL contains no authorization code")
    return code


async def exchange_code(
    session: Any,
    client_id: str,
    redirect_uri: str,
    verifier: str,
    callback_url: str,
) -> PkceToken:
    """Exchange the one-time browser callback code for rotating OAuth tokens."""
    code = extract_authorization_code(callback_url, redirect_uri)
    try:
        async with session.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code_verifier": verifier,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            body = await response.json(content_type=None)
            if not response.ok:
                raise LoginFailed("Yoto rejected the authorization code")
    except LoginFailed:
        raise
    except Exception as err:
        raise LoginFailed("Yoto token exchange failed") from err
    try:
        return PkceToken(
            access_token=str(body["access_token"]),
            refresh_token=str(body["refresh_token"]),
            expires_in=int(body["expires_in"]),
            token_type=str(body.get("token_type", "Bearer")),
            scope=body.get("scope"),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise LoginFailed("Yoto token response was malformed") from err
