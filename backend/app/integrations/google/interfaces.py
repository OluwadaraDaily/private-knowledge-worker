from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True, slots=True)
class GoogleDriveFile:
    """Normalized Google Drive file metadata."""

    id: str
    name: str
    mime_type: str
    parents: tuple[str, ...]
    created_at: datetime | None
    modified_at: datetime | None
    web_url: str | None
    version: str | None = None


@dataclass(frozen=True, slots=True)
class GoogleDriveFilePage:
    """One page of normalized Google Drive file metadata."""

    files: tuple[GoogleDriveFile, ...]
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


class GoogleDriveFileLister(Protocol):
    """Application-facing Google Docs metadata contract."""

    def list_documents(
        self,
        access_token: str,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> GoogleDriveFilePage:
        """Return one page of owned Google Docs metadata."""


class GoogleDriveGateway(
    GoogleDriveVerifier,
    GoogleDriveFolderLister,
    GoogleDriveFileLister,
    Protocol,
):
    """Combined Google Drive client contract."""


@dataclass(frozen=True, slots=True)
class GoogleDocsDocument:
    """Validated raw Google Docs API structure for later normalization."""

    document_id: str
    title: str
    body_content: tuple[dict[str, object], ...]


class GoogleDocsDocumentFetcher(Protocol):
    """Application-facing Google Docs content contract."""

    def get_document(self, access_token: str, document_id: str) -> GoogleDocsDocument:
        """Fetch one Google Doc's structural content."""
