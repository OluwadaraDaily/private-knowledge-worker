from urllib.parse import quote

from app.integrations.google.client import GoogleApiClient, GoogleApiError
from app.integrations.google.interfaces import GoogleDocsDocument

GOOGLE_DOCS_DOCUMENTS_URL = "https://docs.googleapis.com/v1/documents"


class GoogleDocsClient:
    """HTTP client for Google Docs API content requests."""

    def __init__(self, api_client: GoogleApiClient | None = None) -> None:
        self._api_client = api_client if api_client is not None else GoogleApiClient()

    def get_document(self, access_token: str, document_id: str) -> GoogleDocsDocument:
        if not document_id:
            raise ValueError("document_id must not be empty")
        payload = self._api_client.get_json(
            access_token,
            f"{GOOGLE_DOCS_DOCUMENTS_URL}/{quote(document_id, safe='')}",
            params={},
        )
        return _parse_document(payload, document_id)


def _parse_document(payload: object, requested_document_id: str) -> GoogleDocsDocument:
    if not isinstance(payload, dict):
        raise GoogleApiError("Google Docs returned an invalid document response", kind="malformed")
    document_id = payload.get("documentId")
    title = payload.get("title")
    body = payload.get("body")
    content = body.get("content") if isinstance(body, dict) else None
    if (
        document_id != requested_document_id
        or not isinstance(title, str)
        or not isinstance(content, list)
        or not all(isinstance(element, dict) for element in content)
    ):
        raise GoogleApiError("Google Docs returned invalid document metadata", kind="malformed")
    return GoogleDocsDocument(
        document_id=document_id,
        title=title,
        body_content=tuple(content),
    )
