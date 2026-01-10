"""implement_multi_category_missions

Revision ID: 8c7bc8e97742
Revises: c61256d9dc08
Create Date: 2026-01-10 21:01:28.572112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '8c7bc8e97742'
down_revision: Union[str, Sequence[str], None] = 'c61256d9dc08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create mission_category junction table
    op.create_table(
        'mission_category',
        sa.Column('id_mission', sa.Integer(), nullable=False),
        sa.Column('id_categ', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_categ'], ['category.id_categ'], ),
        sa.ForeignKeyConstraint(['id_mission'], ['mission.id_mission'], ),
        sa.PrimaryKeyConstraint('id_mission', 'id_categ')
    )

    # Step 2: Migrate existing data from mission.id_categ to junction table
    op.execute("""
        INSERT INTO mission_category (id_mission, id_categ)
        SELECT id_mission, id_categ
        FROM mission
        WHERE id_categ IS NOT NULL
    """)

    # Step 3: Drop old foreign key and column from mission table
    op.drop_constraint('mission_id_categ_fkey', 'mission', type_='foreignkey')
    op.drop_column('mission', 'id_categ')

    # Step 4: Seed initial categories
    categories = [
        "Aide alimentaire",
        "Accompagnement seniors",
        "Soutien handicap",
        "Aide administrative",
        "Mentorat",
        "Sensibilisation citoyenne",
        "Informatique",
        "Création graphique",
        "Photo & vidéo",
        "Animaux",
        "Biodiversité",
        "Jardinage solidaire",
        "Animation",
        "Arts & loisirs",
        "Organisation événement",
        "Patrimoine culturel",
        "Sport & loisirs",
        "Bien-être",
        "Prévention santé",
        "Logistique terrain",
        "Accueil public",
        "Transport",
        "Bricolage",
        "Collecte dons",
        "Communication",
        "Gestion associative",
        "Recherche financements",
        "Humanitaire",
        "Aide urgence",
    ]

    for category in categories:
        op.execute(f"""
            INSERT INTO category (label)
            SELECT '{category}'
            WHERE NOT EXISTS (SELECT 1 FROM category WHERE label = '{category}')
        """)


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Add back id_categ column to mission table
    op.add_column('mission', sa.Column('id_categ', sa.INTEGER(), nullable=True))

    # Step 2: Migrate data back (take first category if mission has multiple)
    op.execute("""
        UPDATE mission
        SET id_categ = (
            SELECT id_categ FROM mission_category
            WHERE mission_category.id_mission = mission.id_mission
            LIMIT 1
        )
    """)

    # Step 3: Re-create foreign key constraint
    op.create_foreign_key('mission_id_categ_fkey', 'mission', 'category', ['id_categ'], ['id_categ'])

    # Step 4: Drop mission_category junction table
    op.drop_table('mission_category')

    # Note: Seeded categories are NOT removed in downgrade to preserve data
