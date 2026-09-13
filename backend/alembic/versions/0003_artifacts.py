"""0003_artifacts

Revision ID: 0003
Revises: bd4b830def75
Create Date: 2026-09-13

What this migration does:
  - Creates the artifacts table for storing generated Markdown/HTML artifacts.
  - Artifacts are owned by sessions (CASCADE DELETE).

Downgrade:
  - Drops the artifacts table.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: Union[str, None] = 'bd4b830def75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'artifacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('artifact_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('request', sa.Text(), nullable=False),
        sa.Column('grounded', sa.Boolean(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_artifacts_session_id'), 'artifacts', ['session_id'], unique=False)
    op.create_index(op.f('ix_artifacts_created_at'), 'artifacts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_artifacts_created_at'), table_name='artifacts')
    op.drop_index(op.f('ix_artifacts_session_id'), table_name='artifacts')
    op.drop_table('artifacts')
