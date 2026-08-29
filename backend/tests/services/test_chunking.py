import pytest

from app.services.chunking import (
    BASELINE_FIXED_CONFIGURATIONS,
    DocumentChunk,
    FixedTokenChunker,
    HeadingAwareChunker,
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


def test_heading_aware_chunker_preserves_heading_context_and_budget() -> None:
    chunks = HeadingAwareChunker(max_tokens=4).chunk(
        "# Introduction\none two\nthree four\n\n## Details\nfive six"
    )

    assert chunks == (
        DocumentChunk(0, "one two three four", 4, "Introduction"),
        DocumentChunk(1, "five six", 2, "Details"),
    )


def test_heading_aware_chunker_splits_oversized_paragraphs() -> None:
    chunks = HeadingAwareChunker(max_tokens=2).chunk("one two three four five")

    assert chunks == (
        DocumentChunk(0, "one two", 2),
        DocumentChunk(1, "three four", 2),
        DocumentChunk(2, "five", 1),
    )


def test_heading_aware_chunker_rejects_nonpositive_budget() -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        HeadingAwareChunker(0)
