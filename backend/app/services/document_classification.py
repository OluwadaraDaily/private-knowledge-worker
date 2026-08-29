from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

_TYPE_KEYWORDS = {
    "article": "article",
    "paper": "article",
    "research": "article",
    "meeting": "meeting",
    "minutes": "meeting",
    "plan": "plan",
    "project": "plan",
    "note": "notes",
    "notes": "notes",
}


@dataclass(frozen=True, slots=True)
class DocumentClassification:
    """Deterministic document enrichment output."""

    document_type: str
    topics: tuple[str, ...]
    summary: str | None
    method: str
    classified_at: datetime


class DocumentClassifier(Protocol):
    def classify(self, title: str, folder_names: tuple[str, ...]) -> DocumentClassification:
        """Classify a document without changing its content."""


class DeterministicDocumentClassifier:
    """Baseline classifier based on title keywords and folder names."""

    def classify(self, title: str, folder_names: tuple[str, ...]) -> DocumentClassification:
        words = (word.casefold().strip(".,:;!?()[]{}") for word in title.replace("-", " ").split())
        document_type = next(
            (_TYPE_KEYWORDS[word] for word in words if word in _TYPE_KEYWORDS),
            "document",
        )
        topics = tuple(dict.fromkeys(name.strip() for name in folder_names if name.strip()))
        return DocumentClassification(
            document_type=document_type,
            topics=topics,
            summary=None,
            method="deterministic-title-folder-v1",
            classified_at=datetime.now(UTC),
        )
