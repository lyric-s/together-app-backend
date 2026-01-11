"""Add verification_status to association and rejection_reason to document

Revision ID: c61256d9dc08
Revises: 288dd6e558eb
Create Date: 2026-01-10 19:27:11.981651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c61256d9dc08'
down_revision: Union[str, Sequence[str], None] = '288dd6e558eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add verification_status column to association table
    op.add_column(
        'association',
        sa.Column('verification_status', sa.String(), nullable=False, server_default='pending')
    )

    # Add rejection_reason column to document table
    op.add_column(
        'document',
        sa.Column('rejection_reason', sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove rejection_reason column from document table
    op.drop_column('document', 'rejection_reason')

    # Remove verification_status column from association table
    op.drop_column('association', 'verification_status')
