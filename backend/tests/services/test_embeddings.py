from app.services.embeddings import EmbeddingProvider


class FakeEmbeddingProvider:
    model = "test-model"
    dimensions = 3

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((float(len(text)), 0.0, 1.0) for text in texts)


def test_embedding_provider_contract_returns_vectors_in_input_order() -> None:
    provider: EmbeddingProvider = FakeEmbeddingProvider()

    assert provider.model == "test-model"
    assert provider.dimensions == 3
    assert provider.embed(("first", "second")) == ((5.0, 0.0, 1.0), (6.0, 0.0, 1.0))
