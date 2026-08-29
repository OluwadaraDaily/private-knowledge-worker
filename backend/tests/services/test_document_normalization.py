from app.integrations.google.interfaces import GoogleDocsDocument
from app.services.document_normalization import normalize_google_document


def test_normalize_google_document_preserves_headings_paragraphs_lists_and_sections() -> None:
    document = GoogleDocsDocument(
        document_id="doc-1",
        title="Notes",
        body_content=(
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "elements": [{"textRun": {"content": "Overview\n"}}],
                }
            },
            {
                "paragraph": {
                    "elements": [
                        {"textRun": {"content": "First"}},
                        {"textRun": {"content": " paragraph\n"}},
                    ]
                }
            },
            {
                "paragraph": {
                    "bullet": {"listId": "list-1", "nestingLevel": 1},
                    "elements": [{"textRun": {"content": "Nested item\n"}}],
                }
            },
            {"sectionBreak": {}},
            {
                "paragraph": {
                    "bullet": {"listId": "list-1"},
                    "elements": [{"textRun": {"content": "Ordered item\n"}}],
                }
            },
        ),
        lists=(
            {
                "listId": "list-1",
                "listProperties": {
                    "nestingLevels": [{"glyphType": "DECIMAL"}, {"glyphType": "BULLET"}]
                },
            },
        ),
    )

    assert normalize_google_document(document) == (
        "# Overview\nFirst paragraph\n  - Nested item\n\n1. Ordered item"
    )


def test_normalize_google_document_ignores_unsupported_and_malformed_elements() -> None:
    document = GoogleDocsDocument(
        document_id="doc-1",
        title="Empty",
        body_content=(
            {"table": {}},
            {"paragraph": {"elements": [{"inlineObjectElement": {}}]}},
            {"paragraph": {"elements": [{"textRun": {"content": "  kept   text  \n"}}]}},
        ),
    )

    assert normalize_google_document(document) == "kept text"
