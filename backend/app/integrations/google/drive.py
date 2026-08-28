from app.integrations.google.client import GoogleApiClient, GoogleApiError
from app.integrations.google.interfaces import GoogleDriveFolder, GoogleDriveFolderPage

GOOGLE_DRIVE_ABOUT_URL = "https://www.googleapis.com/drive/v3/about"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DRIVE_FOLDER_QUERY = f"mimeType = '{GOOGLE_DRIVE_FOLDER_MIME_TYPE}' and trashed = false"
GOOGLE_DRIVE_FOLDER_FIELDS = "nextPageToken,files(id,name,mimeType,parents,ownedByMe,trashed)"
GOOGLE_DRIVE_MAX_PAGE_SIZE = 1000


class GoogleDriveClient:
    """HTTP client for the Google Drive API."""

    def __init__(self, api_client: GoogleApiClient | None = None) -> None:
        self._api_client = api_client if api_client is not None else GoogleApiClient()

    def verify_access(self, access_token: str) -> None:
        self._api_client.get(
            access_token,
            GOOGLE_DRIVE_ABOUT_URL,
            params={"fields": "user"},
        )

    def list_folders(
        self,
        access_token: str,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> GoogleDriveFolderPage:
        if not 1 <= page_size <= GOOGLE_DRIVE_MAX_PAGE_SIZE:
            raise ValueError("page_size must be between 1 and 1000")

        params = {
            "corpora": "user",
            "fields": GOOGLE_DRIVE_FOLDER_FIELDS,
            "pageSize": str(page_size),
            "q": GOOGLE_DRIVE_FOLDER_QUERY,
            "spaces": "drive",
        }
        if page_token:
            params["pageToken"] = page_token

        payload = self._api_client.get_json(access_token, GOOGLE_DRIVE_FILES_URL, params=params)

        return _parse_folder_page(payload)


def _parse_folder_page(payload: object) -> GoogleDriveFolderPage:
    if not isinstance(payload, dict):
        raise GoogleApiError(
            "Google Drive returned an invalid folder response",
            kind="malformed",
        )

    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        raise GoogleApiError(
            "Google Drive returned an invalid folder response",
            kind="malformed",
        )

    folders: list[GoogleDriveFolder] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, dict):
            raise GoogleApiError(
                "Google Drive returned invalid folder metadata",
                kind="malformed",
            )

        file_id = raw_file.get("id")
        name = raw_file.get("name")
        mime_type = raw_file.get("mimeType")
        if (
            not isinstance(file_id, str)
            or not isinstance(name, str)
            or mime_type != GOOGLE_DRIVE_FOLDER_MIME_TYPE
        ):
            raise GoogleApiError(
                "Google Drive returned invalid folder metadata",
                kind="malformed",
            )

        if raw_file.get("ownedByMe") is not True or raw_file.get("trashed", False) is not False:
            continue

        raw_parents = raw_file.get("parents", [])
        if not isinstance(raw_parents, list):
            raise GoogleApiError(
                "Google Drive returned invalid folder metadata",
                kind="malformed",
            )
        parents: list[str] = []
        for parent in raw_parents:
            if not isinstance(parent, str):
                raise GoogleApiError(
                    "Google Drive returned invalid folder metadata",
                    kind="malformed",
                )
            parents.append(parent)
        folders.append(GoogleDriveFolder(id=file_id, name=name, parents=tuple(parents)))

    raw_next_page_token = payload.get("nextPageToken")
    if raw_next_page_token is not None and not isinstance(raw_next_page_token, str):
        raise GoogleApiError(
            "Google Drive returned an invalid folder response",
            kind="malformed",
        )

    return GoogleDriveFolderPage(
        folders=tuple(folders),
        next_page_token=raw_next_page_token or None,
    )
