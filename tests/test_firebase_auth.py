from time import time

import pytest

from src.inzira.firebase_auth import (
    FirebaseAuthError,
    FirebaseSession,
    refresh_session,
    sign_in_with_password,
)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_sign_in_creates_session_without_retaining_password(monkeypatch):
    def fake_post(url, **kwargs):
        assert "signInWithPassword" in url
        assert kwargs["json"]["password"] == "temporary-password"
        return FakeResponse(
            200,
            {
                "localId": "firebase-uid",
                "email": "ADMIN@EXAMPLE.COM",
                "idToken": "id-token",
                "refreshToken": "refresh-token",
                "expiresIn": "3600",
            },
        )

    monkeypatch.setattr("src.inzira.firebase_auth.requests.post", fake_post)
    session = sign_in_with_password("api-key", "ADMIN@EXAMPLE.COM", "temporary-password")
    assert session.email == "admin@example.com"
    assert session.uid == "firebase-uid"
    assert not hasattr(session, "password")


def test_sign_in_hides_invalid_credential_details(monkeypatch):
    monkeypatch.setattr(
        "src.inzira.firebase_auth.requests.post",
        lambda *args, **kwargs: FakeResponse(400, {"error": {"message": "EMAIL_NOT_FOUND"}}),
    )
    with pytest.raises(FirebaseAuthError, match="email or password"):
        sign_in_with_password("api-key", "unknown@example.com", "wrong")


def test_refresh_skips_network_for_valid_session(monkeypatch):
    session = FirebaseSession(
        uid="uid",
        email="admin@example.com",
        id_token="token",
        refresh_token="refresh",
        expires_at=time() + 600,
    )
    monkeypatch.setattr(
        "src.inzira.firebase_auth.requests.post",
        lambda *args, **kwargs: pytest.fail("A valid token should not be refreshed"),
    )
    assert refresh_session("api-key", session) is session
