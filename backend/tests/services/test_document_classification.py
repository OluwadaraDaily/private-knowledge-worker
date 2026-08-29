from datetime import UTC

from app.services.document_classification import DeterministicDocumentClassifier


def test_deterministic_classifier_uses_title_and_folder_names() -> None:
    result = DeterministicDocumentClassifier().classify(
        "Research plan", (" Projects ", "Research", "Projects")
    )

    assert result.document_type == "article"
    assert result.topics == ("Projects", "Research")
    assert result.summary is None
    assert result.method == "deterministic-title-folder-v1"
    assert result.classified_at.tzinfo == UTC


def test_deterministic_classifier_has_safe_default_for_unknown_titles() -> None:
    result = DeterministicDocumentClassifier().classify("Untitled", ())

    assert result.document_type == "document"
    assert result.topics == ()
