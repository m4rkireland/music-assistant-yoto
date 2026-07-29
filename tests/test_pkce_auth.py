from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest
from music_assistant_models.errors import LoginFailed

from yoto.pkce import build_authorization, extract_authorization_code


def test_pkce_authorization_uses_yoto_library_scope_and_registered_callback() -> None:
    authorization = build_authorization(
        client_id="fixture-client",
        redirect_uri="http://localhost:8095/callback",
        verifier="fixture-verifier-with-enough-entropy-1234567890",
    )

    parsed = urlsplit(authorization.url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://login.yotoplay.com/authorize"
    )
    assert query["client_id"] == ["fixture-client"]
    assert query["redirect_uri"] == ["http://localhost:8095/callback"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["family:library:view offline_access"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    assert "fixture-verifier" not in authorization.url
    assert "fixture-verifier" not in repr(authorization)


def test_callback_code_extraction_accepts_expected_redirect_and_rejects_errors() -> None:
    assert (
        extract_authorization_code(
            "http://localhost:8095/callback?code=fixture-code",
            "http://localhost:8095/callback",
        )
        == "fixture-code"
    )

    with pytest.raises(LoginFailed, match="does not match"):
        extract_authorization_code(
            "http://localhost:9999/callback?code=fixture-code",
            "http://localhost:8095/callback",
        )
    with pytest.raises(LoginFailed, match="denied"):
        extract_authorization_code(
            "http://localhost:8095/callback?error=access_denied&error_description=denied",
            "http://localhost:8095/callback",
        )
