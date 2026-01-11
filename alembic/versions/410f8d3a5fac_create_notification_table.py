"""create notification table

Revision ID: 410f8d3a5fac
Revises: 4c39be31bf29
Create Date: 2026-01-10 23:54:06.815490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '410f8d3a5fac'
down_revision: Union[str, Sequence[str], None] = '4c39be31bf29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create notification_type enum using raw SQL to avoid duplicate creation
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'volunteer_joined', 'volunteer_left', 'volunteer_withdrew',
                'capacity_reached', 'mission_deleted'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Define enum for use in table creation (without creating it again)
    notification_type_enum = ENUM(
        'volunteer_joined', 'volunteer_left', 'volunteer_withdrew',
        'capacity_reached', 'mission_deleted',
        name='notificationtype',
        create_type=False
    )

    # Create notification table
    op.create_table(
        'notification',
        sa.Column('id_notification', sa.Integer(), nullable=False),
        sa.Column('id_asso', sa.Integer(), nullable=False),
        sa.Column('notification_type', notification_type_enum, nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('related_mission_id', sa.Integer(), nullable=True),
        sa.Column('related_user_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['id_asso'], ['association.id_asso'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_mission_id'], ['mission.id_mission'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_user_id'], ['user.id_user'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id_notification')
    )
    op.create_index('ix_notification_association', 'notification', ['id_asso'])
    op.create_index('ix_notification_created_at', 'notification', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notification_created_at', table_name='notification')
    op.drop_index('ix_notification_association', table_name='notification')
    op.drop_table('notification')

    notification_type_enum = ENUM(name='notificationtype')
    notification_type_enum.drop(op.get_bind(), checkfirst=True)
