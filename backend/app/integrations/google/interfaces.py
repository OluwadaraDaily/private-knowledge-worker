from typing import Protocol


class GoogleDriveGateway(Protocol):
    """Application-facing operations supplied by a Google Drive client."""

    def verify_access(self, access_token: str) -> None:
        """Make one authenticated request to Google Drive."""
