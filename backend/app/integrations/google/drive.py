import httpx

GOOGLE_DRIVE_ABOUT_URL = "https://www.googleapis.com/drive/v3/about"


class GoogleDriveError(Exception):
    """Raised when a Google Drive request cannot be completed."""


class GoogleDriveAuthenticationError(GoogleDriveError):
    """Raised when Google Drive rejects the access token."""


class GoogleDriveClient:
    """HTTP client for the Google Drive API."""

    def verify_access(self, access_token: str) -> None:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    GOOGLE_DRIVE_ABOUT_URL,
                    params={"fields": "user"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise GoogleDriveAuthenticationError(
                    "Google Drive rejected the access token"
                ) from error
            raise GoogleDriveError("Google Drive request failed") from error
        except httpx.HTTPError as error:
            raise GoogleDriveError("Google Drive request failed") from error
