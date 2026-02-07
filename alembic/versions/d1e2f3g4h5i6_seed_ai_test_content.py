"""seed ai test content

Revision ID: d1e2f3g4h5i6
Revises: b2a3c4d5e6f7
Create Date: 2026-01-29 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlmodel import Session
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, Sequence[str], None] = 'b2a3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed suspicious content for AI testing."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        print("Skipping AI test data seeding in production.")
        return
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Import inside upgrade to avoid circular dependencies or import issues during migration discovery
    from app.database.init_ai_test_data import init_ai_test_data
    
    try:
        init_ai_test_data(session)
    except Exception as e:
        print(f"Warning: Could not seed AI test data: {e}")
    finally:
        session.close()


def downgrade() -> None:
    """No downgrade for seeded data."""
    pass
