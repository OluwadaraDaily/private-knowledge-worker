from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Unbounded pgvector type; dimensions are validated per index configuration."""

    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "vector"
