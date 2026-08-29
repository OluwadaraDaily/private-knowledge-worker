import pytest

from app.services.index_configurations import (
    IndexConfigurationError,
    validate_index_configuration,
)


def test_validate_index_configuration_accepts_a_reproducible_configuration() -> None:
    validate_index_configuration(
        name="fixed-500-50",
        chunking_strategy="fixed_tokens",
        chunk_size=500,
        chunk_overlap=50,
        embedding_model="text-embedding-model",
        embedding_dimensions=1536,
        retrieval_config={"top_k": 10},
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("name", ""),
        ("chunking_strategy", ""),
        ("embedding_model", ""),
    ),
)
def test_validate_index_configuration_requires_identity_fields(field: str, value: str) -> None:
    values: dict[str, object] = {
        "name": "config",
        "chunking_strategy": "fixed_tokens",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "embedding_model": "model",
        "embedding_dimensions": 1536,
    }
    values[field] = value

    with pytest.raises(IndexConfigurationError):
        validate_index_configuration(**values)  # type: ignore[arg-type]


def test_validate_index_configuration_rejects_invalid_chunking_values() -> None:
    with pytest.raises(IndexConfigurationError, match="smaller"):
        validate_index_configuration(
            name="invalid",
            chunking_strategy="fixed_tokens",
            chunk_size=100,
            chunk_overlap=100,
            embedding_model="model",
            embedding_dimensions=1536,
        )
