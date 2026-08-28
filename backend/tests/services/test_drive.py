import httpx
import pytest

from app.services.drive import (
    GOOGLE_DRIVE_ABOUT_URL,
    GoogleDriveAuthenticationError,
    GoogleDriveClient,
    GoogleDriveError,
)


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return
        request = httpx.Request("GET", GOOGLE_DRIVE_ABOUT_URL)
        response = httpx.Response(self.status_code, request=request)
        raise httpx.HTTPStatusError("request failed", request=request, response=response)


class FakeClient:
    def __init__(self, response: FakeResponse | None = None) -> None:
        self.response = response
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
        if self.response is None:
            raise httpx.TimeoutException("request timed out")
        return self.response


def test_drive_verification_sends_bearer_token_and_minimal_about_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(200))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    GoogleDriveClient("access-token").verify_access()

    assert fake_client.url == GOOGLE_DRIVE_ABOUT_URL
    assert fake_client.params == {"fields": "user"}
    assert fake_client.headers == {"Authorization": "Bearer access-token"}


def test_drive_verification_rejects_unauthorized_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponse(401))
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    with pytest.raises(GoogleDriveAuthenticationError, match="rejected"):
        GoogleDriveClient("expired-token").verify_access()


def test_drive_verification_wraps_network_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    with pytest.raises(GoogleDriveError, match="request failed"):
        GoogleDriveClient("access-token").verify_access()
