from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any

import requests


class FirebaseAuthError(RuntimeError):
    """Raised when Firebase cannot authenticate or refresh a session."""


@dataclass(frozen=True)
class FirebaseSession:
    uid: str
    email: str
    id_token: str
    refresh_token: str
    expires_at: float


def _error_message(response: requests.Response) -> str:
    try:
        code = response.json().get("error", {}).get("message", "")
    except ValueError:
        code = ""
    messages = {
        "EMAIL_NOT_FOUND": "The email or password is incorrect.",
        "INVALID_PASSWORD": "The email or password is incorrect.",
        "INVALID_LOGIN_CREDENTIALS": "The email or password is incorrect.",
        "USER_DISABLED": "This administrator account has been disabled.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please wait and try again.",
    }
    return messages.get(code, "Firebase authentication is temporarily unavailable.")


def sign_in_with_password(api_key: str, email: str, password: str) -> FirebaseSession:
    if not api_key.strip():
        raise FirebaseAuthError("Firebase API key is not configured")
    try:
        response = requests.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
            params={"key": api_key},
            json={"email": email.strip(), "password": password, "returnSecureToken": True},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise FirebaseAuthError("Could not reach Firebase Authentication") from exc
    if response.status_code != 200:
        raise FirebaseAuthError(_error_message(response))
    payload = response.json()
    return FirebaseSession(
        uid=str(payload["localId"]),
        email=str(payload["email"]).lower().strip(),
        id_token=str(payload["idToken"]),
        refresh_token=str(payload["refreshToken"]),
        expires_at=time() + int(payload.get("expiresIn", 3600)) - 60,
    )


def refresh_session(api_key: str, session: FirebaseSession) -> FirebaseSession:
    if session.expires_at > time():
        return session
    try:
        response = requests.post(
            "https://securetoken.googleapis.com/v1/token",
            params={"key": api_key},
            data={"grant_type": "refresh_token", "refresh_token": session.refresh_token},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise FirebaseAuthError("Could not refresh the Firebase session") from exc
    if response.status_code != 200:
        raise FirebaseAuthError("Your administrator session has expired. Sign in again.")
    payload: dict[str, Any] = response.json()
    return FirebaseSession(
        uid=str(payload["user_id"]),
        email=session.email,
        id_token=str(payload["id_token"]),
        refresh_token=str(payload["refresh_token"]),
        expires_at=time() + int(payload.get("expires_in", 3600)) - 60,
    )
