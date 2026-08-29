from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """A deterministic chunk produced from canonical document text."""

    chunk_number: int
    content: str
    token_count: int


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
