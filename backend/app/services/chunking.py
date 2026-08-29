import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """A deterministic chunk produced from canonical document text."""

    chunk_number: int
    content: str
    token_count: int
    heading: str | None = None


class Chunker(Protocol):
    def chunk(self, content: str) -> tuple[DocumentChunk, ...]:
        """Split canonical text into ordered chunks."""


class FixedTokenChunker:
    """Split whitespace-delimited tokens with a fixed overlap."""

    def __init__(self, chunk_size: int, chunk_overlap: int = 0) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must not be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, content: str) -> tuple[DocumentChunk, ...]:
        tokens = content.split()
        if not tokens:
            return ()

        chunks: list[DocumentChunk] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(
                DocumentChunk(
                    chunk_number=len(chunks),
                    content=" ".join(chunk_tokens),
                    token_count=len(chunk_tokens),
                )
            )
            if end == len(tokens):
                break
            start = end - self.chunk_overlap
        return tuple(chunks)


class HeadingAwareChunker:
    """Pack canonical paragraphs by heading while respecting a token budget."""

    _heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(self, max_tokens: int = 800) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.max_tokens = max_tokens

    def chunk(self, content: str) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []
        current_tokens: list[str] = []
        current_heading: str | None = None

        def flush() -> None:
            if current_tokens:
                chunks.append(
                    DocumentChunk(
                        chunk_number=len(chunks),
                        content=" ".join(current_tokens),
                        token_count=len(current_tokens),
                        heading=current_heading,
                    )
                )

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading_match = self._heading_pattern.match(stripped)
            if heading_match:
                flush()
                current_tokens.clear()
                current_heading = heading_match.group(2).strip()
                continue

            paragraph_tokens = stripped.split()
            while paragraph_tokens:
                available = self.max_tokens - len(current_tokens)
                if available == 0:
                    flush()
                    current_tokens.clear()
                    continue
                current_tokens.extend(paragraph_tokens[:available])
                del paragraph_tokens[:available]
                if paragraph_tokens:
                    flush()
                    current_tokens.clear()

        flush()
        return tuple(chunks)


BASELINE_FIXED_CONFIGURATIONS = {
    "fixed-500-50": (500, 50),
    "fixed-1000-100": (1000, 100),
}


def baseline_fixed_chunker(name: str) -> FixedTokenChunker:
    """Return a fixed-token chunker for one of the supported V1 baselines."""
    configuration = BASELINE_FIXED_CONFIGURATIONS.get(name)
    if configuration is None:
        raise ValueError(f"Unknown baseline chunking configuration: {name}")
    return FixedTokenChunker(*configuration)
