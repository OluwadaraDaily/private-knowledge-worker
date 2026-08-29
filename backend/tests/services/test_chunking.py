import pytest

from app.services.chunking import (
    BASELINE_FIXED_CONFIGURATIONS,
    DocumentChunk,
    FixedTokenChunker,
    baseline_fixed_chunker,
)


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


def test_baseline_fixed_configurations_have_reproducible_parameters() -> None:
    assert BASELINE_FIXED_CONFIGURATIONS == {
        "fixed-500-50": (500, 50),
        "fixed-1000-100": (1000, 100),
    }
    assert baseline_fixed_chunker("fixed-500-50").chunk_size == 500
    assert baseline_fixed_chunker("fixed-500-50").chunk_overlap == 50
    assert baseline_fixed_chunker("fixed-1000-100").chunk_size == 1000
    assert baseline_fixed_chunker("fixed-1000-100").chunk_overlap == 100


def test_baseline_fixed_chunker_rejects_unknown_configuration() -> None:
    with pytest.raises(ValueError, match="Unknown baseline"):
        baseline_fixed_chunker("unknown")
