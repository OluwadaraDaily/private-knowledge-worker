from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.index_config import IndexConfig


class IndexConfigurationError(ValueError):
    """Raised when an index configuration is invalid or unavailable."""


def validate_index_configuration(
    *,
    name: str,
    chunking_strategy: str,
    chunk_size: int | None,
    chunk_overlap: int | None,
    embedding_model: str,
    embedding_dimensions: int,
    retrieval_config: Mapping[str, object] | None = None,
) -> None:
    """Validate configuration values before writing them to the database."""
    if not name.strip() or not chunking_strategy.strip() or not embedding_model.strip():
        raise IndexConfigurationError("Index configuration names and strategies are required")
    if embedding_dimensions <= 0:
        raise IndexConfigurationError("Embedding dimensions must be positive")
    if chunk_size is not None and chunk_size <= 0:
        raise IndexConfigurationError("Chunk size must be positive")
    if chunk_overlap is not None and chunk_overlap < 0:
        raise IndexConfigurationError("Chunk overlap must not be negative")
    if chunk_size is not None and chunk_overlap is not None and chunk_overlap >= chunk_size:
        raise IndexConfigurationError("Chunk overlap must be smaller than chunk size")
    if retrieval_config is not None and not isinstance(retrieval_config, Mapping):
        raise IndexConfigurationError("Retrieval configuration must be an object")


def create_index_configuration(
    session: Session,
    *,
    name: str,
    chunking_strategy: str,
    chunk_size: int | None,
    chunk_overlap: int | None,
    embedding_model: str,
    embedding_dimensions: int,
    retrieval_config: Mapping[str, object] | None = None,
    is_active: bool = False,
) -> IndexConfig:
    validate_index_configuration(
        name=name,
        chunking_strategy=chunking_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        retrieval_config=retrieval_config,
    )
    if is_active:
        _deactivate_all(session)
    config = IndexConfig(
        name=name,
        chunking_strategy=chunking_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        retrieval_config=dict(retrieval_config) if retrieval_config is not None else None,
        is_active=is_active,
    )
    session.add(config)
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return config


def get_active_index_configuration(session: Session) -> IndexConfig:
    config = session.scalar(select(IndexConfig).where(IndexConfig.is_active.is_(True)))
    if config is None:
        raise IndexConfigurationError("No active index configuration is available")
    return config


def activate_index_configuration(session: Session, config_id: UUID) -> IndexConfig:
    config = session.get(IndexConfig, config_id)
    if config is None:
        raise IndexConfigurationError("Index configuration was not found")
    _deactivate_all(session)
    config.is_active = True
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return config


def _deactivate_all(session: Session) -> None:
    for config in session.scalars(select(IndexConfig).where(IndexConfig.is_active.is_(True))):
        config.is_active = False
