"""create ai_report table

Revision ID: b2a3c4d5e6f7
Revises: 065f503f6693
Create Date: 2026-01-29 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2a3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "065f503f6693"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create ai_report table."""
    
    # 1. Create the new enum type safely
    ai_category_type = postgresql.ENUM(
        "NORMAL_CONTENT",
        "TOXIC_LANGUAGE",
        "INAPPROPRIATE_CONTENT",
        "SPAM_LIKE",
        "FRAUD_SUSPECTED",
        "MISLEADING_INFORMATION",
        "OTHER",
        name="aicontentcategory",
    )
    ai_category_type.create(op.get_bind(), checkfirst=True)

    # 2. Create the table using existing types (create_type=False)
    op.create_table(
        "ai_report",
        sa.Column("id_report", sa.Integer(), nullable=False),
        sa.Column(
            "target", 
            postgresql.ENUM(name="reporttarget", create_type=False), 
            nullable=False
        ),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column(
            "classification", 
            postgresql.ENUM(name="aicontentcategory", create_type=False), 
            nullable=False
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column(
            "state", 
            postgresql.ENUM(name="processingstatus", create_type=False), 
            nullable=False
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id_report"),
    )


def downgrade() -> None:
    """Downgrade schema: drop ai_report table."""
    op.drop_table("ai_report")
    # On supprime le type personnalisé que nous avons créé
    op.execute("DROP TYPE IF EXISTS aicontentcategory")