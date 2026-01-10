"""add password reset to user

Revision ID: 4c39be31bf29
Revises: 8c7bc8e97742
Create Date: 2026-01-10 22:22:21.769517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4c39be31bf29'
down_revision: Union[str, Sequence[str], None] = '8c7bc8e97742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add password reset fields to user table."""
    # Add password_reset_token column
    op.add_column('user', sa.Column('password_reset_token', sa.String(), nullable=True))

    # Add password_reset_expires column
    op.add_column('user', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))

    # Add index on password_reset_token for faster lookups
    op.create_index(op.f('ix_user_password_reset_token'), 'user', ['password_reset_token'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Remove password reset fields from user table."""
    # Drop index
    op.drop_index(op.f('ix_user_password_reset_token'), table_name='user')

    # Drop columns
    op.drop_column('user', 'password_reset_expires')
    op.drop_column('user', 'password_reset_token')
