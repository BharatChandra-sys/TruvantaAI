"""HNSW vector indexes and full-text indexes for claim memory

IVFFlat partitions vectors into lists chosen when the index is built. These
were built on nearly empty tables with lists=100, and a query probes one list
by default, so most stored vectors were never found. HNSW needs no training
data, keeps high recall as rows are added, and suits this read-heavy use.

The GIN indexes back the BM25-style full-text search in retrieval/hybrid.py,
which otherwise computes to_tsvector for every row on every query.

Revision ID: 20261025000000
Revises: 20260920000000
"""
from alembic import op

revision = '20261025000000'
down_revision = '20260920000000'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade():
    if not _is_postgres():
        return
    op.execute("DROP INDEX IF EXISTS ix_fact_checks_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_evidence_embedding_ivfflat")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_fact_checks_embedding_hnsw
                  ON fact_checks USING hnsw (embedding vector_cosine_ops)
                  WITH (m = 16, ef_construction = 64)""")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_evidence_embedding_hnsw
                  ON evidence_documents USING hnsw (embedding vector_cosine_ops)
                  WITH (m = 16, ef_construction = 64)""")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_fact_checks_claim_fts
                  ON fact_checks USING gin (to_tsvector('english', claim_text))""")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_evidence_fts
                  ON evidence_documents USING gin
                  (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,'')))""")


def downgrade():
    if not _is_postgres():
        return
    op.execute("DROP INDEX IF EXISTS ix_evidence_fts")
    op.execute("DROP INDEX IF EXISTS ix_fact_checks_claim_fts")
    op.execute("DROP INDEX IF EXISTS ix_evidence_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_fact_checks_embedding_hnsw")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_fact_checks_embedding_ivfflat
                  ON fact_checks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)""")
    op.execute("""CREATE INDEX IF NOT EXISTS ix_evidence_embedding_ivfflat
                  ON evidence_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)""")
