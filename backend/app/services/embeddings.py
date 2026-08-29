from typing import Protocol


class EmbeddingProvider(Protocol):
    """Application-facing contract for embedding canonical chunks or queries."""

    @property
    def model(self) -> str:
        """Return the provider model identifier."""

    @property
    def dimensions(self) -> int:
        """Return the vector dimension produced by this provider."""

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Embed texts in order and return one vector per input."""
