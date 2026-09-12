"""Add knowledge base: transcripts and chunks tables with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-09-12

What this migration does:
  - Enables the pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)
  - Creates the transcripts table (episode metadata)
  - Creates the chunks table (content chunks with 768-dim embeddings)
  - Adds indexes for retrieval performance

Downgrade:
  - Drops chunks table, then transcripts table
  - Does NOT drop the vector extension — future migrations may depend on it
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Create transcripts table
    op.create_table(
        "transcripts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("episode_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("guest_name", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("episode_id", name="uq_transcripts_episode_id"),
    )
    op.create_index("ix_transcripts_episode_id", "transcripts", ["episode_id"])

    # 3. Create chunks table
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "transcript_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transcripts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("timestamp_start", sa.Float(), nullable=True),
        sa.Column("timestamp_end", sa.Float(), nullable=True),
        sa.Column(
            "embedding",
            Vector(EMBEDDING_DIM),
            nullable=False,
            comment="768-dimensional embedding vector (nomic-embed-text)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_chunks_transcript_id", "chunks", ["transcript_id"])
    op.create_index("ix_chunks_chunk_index", "chunks", ["chunk_index"])
    op.create_index(
        "ix_chunks_transcript_chunk",
        "chunks",
        ["transcript_id", "chunk_index"],
    )

    # 4. HNSW index for approximate nearest-neighbor cosine search.
    #    HNSW is preferred over IVFFlat: better recall, no training required,
    #    and works well even with small datasets.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    # Drop chunks first (FK dependency)
    op.drop_table("chunks")
    # Drop transcripts
    op.drop_table("transcripts")
    # NOTE: vector extension is intentionally NOT dropped.
    # Future migrations may depend on it and DROP EXTENSION CASCADE
    # could silently remove other objects.
