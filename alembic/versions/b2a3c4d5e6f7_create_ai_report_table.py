"""create ai_report table

Revision ID: b2a3c4d5e6f7
Revises: 065f503f6693
Create Date: 2026-01-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2a3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '065f503f6693'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create ai_report table."""
    # Create the AIContentCategory enum type if it doesn't exist
    aicontentcategory_enum = sa.Enum(
        'NORMAL_CONTENT', 'TOXIC_LANGUAGE', 'INAPPROPRIATE_CONTENT',
        'SPAM_LIKE', 'FRAUD_SUSPECTED', 'MISLEADING_INFORMATION', 'OTHER',
        name='aicontentcategory'
    )
    aicontentcategory_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'ai_report',
        sa.Column('id_report', sa.Integer(), nullable=False),
        sa.Column(
            'target',
            sa.Enum('PROFILE', 'MESSAGE', 'MISSION', 'OTHER', name='reporttarget'),
            nullable=False
        ),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column(
            'classification',
            sa.Enum(
                'NORMAL_CONTENT', 'TOXIC_LANGUAGE', 'INAPPROPRIATE_CONTENT',
                'SPAM_LIKE', 'FRAUD_SUSPECTED', 'MISLEADING_INFORMATION', 'OTHER',
                name='aicontentcategory'
            ),
            nullable=False
        ),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('model_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            'state',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='processingstatus'),
            nullable=False
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id_report')
    )


def downgrade() -> None:
    """Downgrade schema: drop ai_report table."""
    op.drop_table('ai_report')
    op.execute("DROP TYPE IF EXISTS aicontentcategory")