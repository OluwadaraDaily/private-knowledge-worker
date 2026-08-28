from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GoogleDriveFolder:
    """Normalized folder metadata returned by Google Drive."""

    id: str
    name: str
    parents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GoogleDriveFolderPage:
    """One page of normalized Google Drive folders."""

    folders: tuple[GoogleDriveFolder, ...]
    next_page_token: str | None


class GoogleDriveVerifier(Protocol):
    """Application-facing access-verification operation."""

    def verify_access(self, access_token: str) -> None:
        """Make one authenticated request to Google Drive."""


class GoogleDriveFolderLister(Protocol):
    """Application-facing folder-listing operation."""

    def list_folders(
        self,
        access_token: str,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> GoogleDriveFolderPage:
        """Return one page of owned, non-trashed folders."""


class GoogleDriveGateway(GoogleDriveVerifier, GoogleDriveFolderLister, Protocol):
    """Combined Google Drive client contract."""
