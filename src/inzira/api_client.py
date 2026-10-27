from __future__ import annotations

from typing import Any

import httpx

from src.inzira.inference import ScreeningResult


class InferenceAPIError(RuntimeError):
    """Raised when the remote inference service cannot return a valid result."""


def run_remote_screening(
    *,
    api_url: str,
    answers: dict[str, Any],
    api_key: str = "",
    timeout_seconds: float = 12.0,
) -> ScreeningResult:
    endpoint = api_url.rstrip("/") + "/v1/screenings"
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        response = httpx.post(
            endpoint,
            json=answers,
            headers=headers,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return ScreeningResult(
            score=float(payload["score"]),
            threshold=float(payload["threshold"]),
            elevated_risk=bool(payload["elevated_risk"]),
            completeness=float(payload["completeness"]),
            limited_information=bool(payload["limited_information"]),
            small_household=bool(payload["small_household"]),
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise InferenceAPIError("The screening API is unavailable or returned an invalid response") from exc
