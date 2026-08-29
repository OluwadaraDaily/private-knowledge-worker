import pytest

from app.services.chunking import DocumentChunk, FixedTokenChunker


def test_fixed_token_chunker_returns_ordered_overlapping_chunks() -> None:
    chunks = FixedTokenChunker(chunk_size=4, chunk_overlap=1).chunk(
        "one two three four five six seven"
    )

    assert chunks == (
        DocumentChunk(0, "one two three four", 4),
        DocumentChunk(1, "four five six seven", 4),
    )


def test_fixed_token_chunker_handles_empty_content() -> None:
    assert FixedTokenChunker(4).chunk("   ") == ()


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    ((0, 0), (4, -1), (4, 4)),
)
def test_fixed_token_chunker_rejects_invalid_configuration(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    with pytest.raises(ValueError):
        FixedTokenChunker(chunk_size, chunk_overlap)
