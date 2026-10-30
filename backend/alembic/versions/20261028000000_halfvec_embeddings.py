"""Store embeddings as halfvec (16-bit floats)

halfvec halves the storage and HNSW index memory of the embedding columns.
Cosine similarity between 384-dim unit vectors moves by under 0.0001 (measured
on 20,000 pairs), far inside the smallest gap the memory thresholds rely on
(0.005 between Gemini's match threshold and the closest rewordings).

halfvec needs pgvector 0.7.0 or later. The migration updates the extension
when it is older and stops with a clear error if that is not possible,
rather than leaving the code and the columns on different types.

Revision ID: 20261028000000
Revises: 20261025000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20261028000000'
down_revision = '20261025000000'
branch_labels = None
depends_on = None

_TABLES = (("fact_checks", "ix_fact_checks_embedding_hnsw"),
           ("evidence_documents", "ix_evidence_embedding_hnsw"))


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _pgvector_version():
    row = op.get_bind().execute(sa.text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")).first()
    return tuple(int(x) for x in row[0].split(".")[:3]) if row else None


def _convert(column_type: str, ops: str):
    for table, index in _TABLES:
        op.execute(f"DROP INDEX IF EXISTS {index}")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN embedding TYPE {column_type}(384) "
                   f"USING embedding::{column_type}(384)")
        op.execute(f"""CREATE INDEX IF NOT EXISTS {index}
                       ON {table} USING hnsw (embedding {ops})
                       WITH (m = 16, ef_construction = 64)""")


def upgrade():
    if not _is_postgres():
        return
    version = _pgvector_version()
    if version is None:
        return          # no pgvector: the embedding columns are text and stay so
    if version < (0, 7, 0):
        op.execute("ALTER EXTENSION vector UPDATE")
        version = _pgvector_version()
        if version < (0, 7, 0):
            raise RuntimeError(f"halfvec needs pgvector 0.7.0 or later; this database has "
                               f"{'.'.join(map(str, version))} and it could not be updated")
    _convert("halfvec", "halfvec_cosine_ops")


def downgrade():
    if not _is_postgres() or _pgvector_version() is None:
        return
    _convert("vector", "vector_cosine_ops")
