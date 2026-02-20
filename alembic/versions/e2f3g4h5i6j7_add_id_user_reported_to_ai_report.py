"""Add id_user_reported to AIReport

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-02-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add id_user_reported column to ai_report table."""
    # We allow nullable initially to avoid issues with existing data if any, 
    # but the service will always populate it.
    op.add_column('ai_report', sa.Column('id_user_reported', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_ai_report_user_reported', 'ai_report', 'user', ['id_user_reported'], ['id_user'])


def downgrade() -> None:
    """Remove id_user_reported column from ai_report table."""
    op.drop_constraint('fk_ai_report_user_reported', 'ai_report', type_='foreignkey')
    op.drop_column('ai_report', 'id_user_reported')
