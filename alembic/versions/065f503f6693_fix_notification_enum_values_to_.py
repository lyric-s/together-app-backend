"""fix notification enum values to uppercase

Revision ID: 065f503f6693
Revises: 32ee6493ed3c
Create Date: 2026-01-15 01:24:56.039405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '065f503f6693'
down_revision: Union[str, Sequence[str], None] = '32ee6493ed3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Migrates notificationtype enum from lowercase to uppercase values to match
    SQLModel serialization behavior (uses enum name, not value).
    """
    # Step 1: Rename old enum type
    op.execute("ALTER TYPE notificationtype RENAME TO notificationtype_old")

    # Step 2: Create new enum type with uppercase values
    op.execute("""
        CREATE TYPE notificationtype AS ENUM (
            'VOLUNTEER_JOINED', 'VOLUNTEER_LEFT', 'VOLUNTEER_WITHDREW',
            'CAPACITY_REACHED', 'MISSION_DELETED'
        )
    """)

    # Step 3: Update notification table to use new enum
    # Convert lowercase to uppercase during migration
    op.execute("""
        ALTER TABLE notification
        ALTER COLUMN notification_type TYPE notificationtype
        USING (
            CASE notification_type::text
                WHEN 'volunteer_joined' THEN 'VOLUNTEER_JOINED'::notificationtype
                WHEN 'volunteer_left' THEN 'VOLUNTEER_LEFT'::notificationtype
                WHEN 'volunteer_withdrew' THEN 'VOLUNTEER_WITHDREW'::notificationtype
                WHEN 'capacity_reached' THEN 'CAPACITY_REACHED'::notificationtype
                WHEN 'mission_deleted' THEN 'MISSION_DELETED'::notificationtype
            END
        )
    """)

    # Step 4: Drop old enum type
    op.execute("DROP TYPE notificationtype_old")


def downgrade() -> None:
    """
    Downgrade schema.

    Reverts notificationtype enum from uppercase to lowercase values.
    """
    # Step 1: Rename current enum type
    op.execute("ALTER TYPE notificationtype RENAME TO notificationtype_new")

    # Step 2: Recreate old enum type with lowercase values
    op.execute("""
        CREATE TYPE notificationtype AS ENUM (
            'volunteer_joined', 'volunteer_left', 'volunteer_withdrew',
            'capacity_reached', 'mission_deleted'
        )
    """)

    # Step 3: Update notification table to use old enum
    # Convert uppercase to lowercase during migration
    op.execute("""
        ALTER TABLE notification
        ALTER COLUMN notification_type TYPE notificationtype
        USING (
            CASE notification_type::text
                WHEN 'VOLUNTEER_JOINED' THEN 'volunteer_joined'::notificationtype
                WHEN 'VOLUNTEER_LEFT' THEN 'volunteer_left'::notificationtype
                WHEN 'VOLUNTEER_WITHDREW' THEN 'volunteer_withdrew'::notificationtype
                WHEN 'CAPACITY_REACHED' THEN 'capacity_reached'::notificationtype
                WHEN 'MISSION_DELETED' THEN 'mission_deleted'::notificationtype
            END
        )
    """)

    # Step 4: Drop new enum type
    op.execute("DROP TYPE notificationtype_new")
