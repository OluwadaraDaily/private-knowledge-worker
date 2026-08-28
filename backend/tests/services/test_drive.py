import time

import httpx
import pytest

from app.integrations.google.client import GoogleApiError
from app.integrations.google.drive import (
    GOOGLE_DRIVE_ABOUT_URL,
    GOOGLE_DRIVE_FILES_URL,
    GOOGLE_DRIVE_FOLDER_FIELDS,
    GOOGLE_DRIVE_FOLDER_QUERY,
    GoogleDriveClient,
)
from app.integrations.google.interfaces import GoogleDriveFolder, GoogleDriveFolderPage


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return
        request = httpx.Request("GET", GOOGLE_DRIVE_ABOUT_URL)
        response = httpx.Response(self.status_code, request=request)
        raise httpx.HTTPStatusError("request failed", request=request, response=response)

    def json(self) -> object:
        if self.payload is None:
            raise ValueError("response payload is unavailable")
        return self.payload


class FakeClient:
    def __init__(self, *responses: FakeResponse | BaseException) -> None:
        self.responses = list(responses)
        self.url: str | None = None
        self.params: dict[str, str] | None = None
        self.headers: dict[str, str] | None = None

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> FakeResponse:
        self.url = url
        self.params = params
        self.headers = headers
        if not self.responses:
            raise httpx.TimeoutException("request timed out")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def test_drive_verification_sends_bearer_token_and_minimal_about_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(200, {}))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    GoogleDriveClient().verify_access("access-token")

    assert fake_client.url == GOOGLE_DRIVE_ABOUT_URL
    assert fake_client.params == {"fields": "user"}
    assert fake_client.headers == {"Authorization": "Bearer access-token"}


def test_drive_verification_rejects_unauthorized_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(401))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    with pytest.raises(GoogleApiError, match="rejected") as error:
        GoogleDriveClient().verify_access("expired-token")
    assert error.value.kind == "authentication"


def test_drive_verification_wraps_network_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    with pytest.raises(GoogleApiError, match="request failed") as error:
        GoogleDriveClient().verify_access("access-token")
    assert error.value.kind == "transient"


def test_drive_verification_retries_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeClient(httpx.TimeoutException("request timed out"), FakeResponse(200, {}))
    sleeps: list[float] = []
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(time, "sleep", sleeps.append)

    GoogleDriveClient().verify_access("access-token")

    assert sleeps == [0.5]


def test_drive_requests_retry_rate_limits_and_honor_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limited = FakeResponse(
        429,
        {"error": {"errors": [{"reason": "rateLimitExceeded"}]}},
        headers={"Retry-After": "2"},
    )
    fake_client = FakeClient(rate_limited, FakeResponse(200, {}))
    sleeps: list[float] = []
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(time, "sleep", sleeps.append)

    GoogleDriveClient().verify_access("access-token")

    assert sleeps == [2.0]


def test_drive_requests_exhausted_rate_limits_raise_a_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limited = FakeResponse(
        403,
        {"error": {"errors": [{"reason": "userRateLimitExceeded"}]}},
    )
    fake_client = FakeClient(rate_limited, rate_limited, rate_limited)
    sleeps: list[float] = []
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(time, "sleep", sleeps.append)

    with pytest.raises(GoogleApiError) as error:
        GoogleDriveClient().verify_access("access-token")

    assert error.value.kind == "rate_limit"
    assert error.value.retry_after_seconds is None
    assert sleeps == [0.5, 1.0]


def test_drive_folder_listing_sends_pagination_and_ownership_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(
        FakeResponse(
            200,
            {
                "nextPageToken": "next-page",
                "files": [
                    {
                        "id": "folder-1",
                        "name": "Projects",
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": ["root"],
                        "ownedByMe": True,
                        "trashed": False,
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    page = GoogleDriveClient().list_folders(
        "access-token",
        page_token="previous-page",
        page_size=25,
    )

    assert fake_client.url == GOOGLE_DRIVE_FILES_URL
    assert fake_client.params == {
        "corpora": "user",
        "fields": GOOGLE_DRIVE_FOLDER_FIELDS,
        "pageSize": "25",
        "q": GOOGLE_DRIVE_FOLDER_QUERY,
        "spaces": "drive",
        "pageToken": "previous-page",
    }
    assert page == GoogleDriveFolderPage(
        folders=(GoogleDriveFolder(id="folder-1", name="Projects", parents=("root",)),),
        next_page_token="next-page",
    )


def test_drive_folder_listing_rejects_malformed_folder_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(200, {"files": [{"id": "folder-1"}]}))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    with pytest.raises(GoogleApiError, match="invalid folder metadata") as error:
        GoogleDriveClient().list_folders("access-token")
    assert error.value.kind == "malformed"


def test_drive_folder_listing_rejects_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(200))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    with pytest.raises(GoogleApiError, match="invalid JSON") as error:
        GoogleDriveClient().list_folders("access-token")
    assert error.value.kind == "malformed"


def test_drive_folder_listing_excludes_unowned_and_trashed_folders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(
        FakeResponse(
            200,
            {
                "files": [
                    {
                        "id": "owned-folder",
                        "name": "Owned",
                        "mimeType": "application/vnd.google-apps.folder",
                        "ownedByMe": True,
                        "trashed": False,
                    },
                    {
                        "id": "shared-folder",
                        "name": "Shared",
                        "mimeType": "application/vnd.google-apps.folder",
                        "ownedByMe": False,
                        "trashed": False,
                    },
                    {
                        "id": "trashed-folder",
                        "name": "Trashed",
                        "mimeType": "application/vnd.google-apps.folder",
                        "ownedByMe": True,
                        "trashed": True,
                    },
                ]
            },
        )
    )
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    page = GoogleDriveClient().list_folders("access-token")

    assert [folder.id for folder in page.folders] == ["owned-folder"]
