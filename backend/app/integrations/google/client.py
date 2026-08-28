import math
import time
from typing import Literal

import httpx

GoogleApiErrorKind = Literal[
    "authentication",
    "rate_limit",
    "transient",
    "upstream",
    "malformed",
]

GOOGLE_API_TIMEOUT_SECONDS = 10.0
GOOGLE_API_MAX_ATTEMPTS = 3
GOOGLE_API_RETRY_BASE_SECONDS = 0.5
GOOGLE_API_MAX_RETRY_DELAY_SECONDS = 5.0
GOOGLE_API_RETRYABLE_STATUS_CODES = frozenset({408, 500, 502, 503, 504})
GOOGLE_API_RATE_LIMIT_REASONS = frozenset(
    {
        "backendError",
        "dailyLimitExceeded",
        "rateLimitExceeded",
        "sharingRateLimitExceeded",
        "userRateLimitExceeded",
    }
)


class GoogleApiError(Exception):
    """A safe, classified failure from an authenticated Google API request."""

    def __init__(
        self,
        message: str,
        *,
        kind: GoogleApiErrorKind = "upstream",
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.kind = kind
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class GoogleApiClient:
    """Shared HTTP boundary for authenticated Google JSON API requests."""

    def get(
        self,
        access_token: str,
        url: str,
        *,
        params: dict[str, str],
    ) -> httpx.Response:
        """Make an authenticated GET after applying shared error handling."""
        return self._get(access_token, url, params=params)

    def get_json(
        self,
        access_token: str,
        url: str,
        *,
        params: dict[str, str],
    ) -> object:
        response = self.get(access_token, url, params=params)
        try:
            return response.json()
        except (TypeError, ValueError) as error:
            raise GoogleApiError(
                "Google returned an invalid JSON response",
                kind="malformed",
            ) from error

    def _get(
        self,
        access_token: str,
        url: str,
        *,
        params: dict[str, str],
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=GOOGLE_API_TIMEOUT_SECONDS) as client:
            for attempt in range(GOOGLE_API_MAX_ATTEMPTS):
                try:
                    response = client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as error:
                    status_code = response.status_code
                    is_rate_limited = status_code == 429 or (
                        status_code == 403 and _response_is_rate_limited(response)
                    )
                    if status_code == 401 or (status_code == 403 and not is_rate_limited):
                        raise GoogleApiError(
                            "Google authentication was rejected",
                            kind="authentication",
                            status_code=status_code,
                        ) from error
                    if is_rate_limited:
                        if attempt < GOOGLE_API_MAX_ATTEMPTS - 1:
                            time.sleep(_retry_delay(attempt, response))
                            continue
                        raise GoogleApiError(
                            "Google API rate limit exceeded",
                            kind="rate_limit",
                            status_code=status_code,
                            retry_after_seconds=_retry_after_seconds(response),
                        ) from error
                    if status_code in GOOGLE_API_RETRYABLE_STATUS_CODES:
                        if attempt < GOOGLE_API_MAX_ATTEMPTS - 1:
                            time.sleep(_retry_delay(attempt, response))
                            continue
                        raise GoogleApiError(
                            "Google API request failed",
                            kind="transient",
                            status_code=status_code,
                        ) from error
                    raise GoogleApiError(
                        "Google API request failed",
                        status_code=status_code,
                    ) from error
                except httpx.TimeoutException as error:
                    if attempt < GOOGLE_API_MAX_ATTEMPTS - 1:
                        time.sleep(_retry_delay(attempt, None))
                        continue
                    raise GoogleApiError(
                        "Google API request failed",
                        kind="transient",
                    ) from error
                except httpx.RequestError as error:
                    if attempt < GOOGLE_API_MAX_ATTEMPTS - 1:
                        time.sleep(_retry_delay(attempt, None))
                        continue
                    raise GoogleApiError(
                        "Google API request failed",
                        kind="transient",
                    ) from error

        raise GoogleApiError("Google API request failed", kind="transient")


def _response_is_rate_limited(response: httpx.Response) -> bool:
    try:
        payload: object = response.json()
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    raw_error = payload.get("error")
    if not isinstance(raw_error, dict):
        return False
    raw_errors = raw_error.get("errors")
    if not isinstance(raw_errors, list):
        return False
    return any(
        isinstance(item, dict) and item.get("reason") in GOOGLE_API_RATE_LIMIT_REASONS
        for item in raw_errors
    )


def _retry_after_seconds(response: httpx.Response) -> int | None:
    raw_value = response.headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        seconds = float(raw_value)
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return min(math.ceil(seconds), math.ceil(GOOGLE_API_MAX_RETRY_DELAY_SECONDS))


def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
    if response is not None:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return float(retry_after)
    delay = GOOGLE_API_RETRY_BASE_SECONDS * (2**attempt)
    return float(min(delay, GOOGLE_API_MAX_RETRY_DELAY_SECONDS))
