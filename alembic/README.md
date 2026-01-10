# Database Migrations with Alembic

This directory contains database migration scripts managed by [Alembic](https://alembic.sqlalchemy.org/), the database migration tool for [SQLAlchemy](https://www.sqlalchemy.org/).

## Overview

Alembic provides version control for your database schema, allowing you to:
- Track database schema changes over time
- Apply migrations incrementally across environments
- Roll back changes if needed
- Collaborate with team members on schema changes

## Directory Structure

```
alembic/
├── env.py              # Migration environment configuration
├── script.py.mako      # Template for new migration files
├── versions/           # Migration scripts (chronologically ordered)
│   ├── fe5fe30b5dd1_initial_migration.py
│   ├── f8e229cd6650_user_and_admin_related_tables_.py
│   └── ...
└── README.md          # This file
```

## Common Commands

### Apply Migrations

```bash
# Upgrade to the latest version
uv run alembic upgrade head

# Upgrade by one version
uv run alembic upgrade +1

# Upgrade to a specific version
uv run alembic upgrade <revision_id>
```

### Create New Migrations

```bash
# Auto-generate a migration from model changes
uv run alembic revision --autogenerate -m "Description of changes"

# Create an empty migration (for manual editing)
uv run alembic revision -m "Description of changes"
```

> [!IMPORTANT]
> **Always review auto-generated migrations** before applying them. Alembic may not detect all changes (like column renames or data migrations) and might generate incorrect operations.

### View Migration History

```bash
# Show current version
uv run alembic current

# Show migration history
uv run alembic history --verbose

# Show SQL that would be executed (without applying)
uv run alembic upgrade head --sql
```

### Rollback Migrations

```bash
# Downgrade by one version
uv run alembic downgrade -1

# Downgrade to a specific version
uv run alembic downgrade <revision_id>

# Downgrade all migrations (back to empty database)
uv run alembic downgrade base
```

## Creating Migrations

### 1. Auto-generate from Model Changes

After modifying your [SQLModel](https://sqlmodel.tiangolo.com/) models in `app/models/`:

```bash
# Generate migration
uv run alembic revision --autogenerate -m "Add user profile fields"

# Review the generated file in alembic/versions/
# Edit if necessary to fix any issues

# Apply the migration
uv run alembic upgrade head
```

### 2. Manual Migration

For complex changes (data migrations, custom SQL, etc.):

```bash
# Create empty migration
uv run alembic revision -m "Migrate user data to new format"

# Edit the generated file and add your custom logic
# Then apply
uv run alembic upgrade head
```

## Migration Best Practices

### Before Creating a Migration

1. **Pull latest changes** from the repository
2. **Apply existing migrations** to ensure your database is up-to-date
3. **Make your model changes** in `app/models/`
4. **Test locally** before committing

### When Writing Migrations

1. **Use descriptive names**: `add_user_profile_fields` not `update_users`
2. **Keep migrations focused**: One logical change per migration
3. **Write reversible migrations**: Always implement `downgrade()` when possible
4. **Test both directions**: Ensure `upgrade` and `downgrade` work correctly
5. **Avoid data loss**: Be careful with operations like `drop_column()` or `drop_table()`
6. **Handle NULL constraints carefully**: Add columns as nullable first, populate data, then add constraints

### Example: Safe Column Addition

```python
# Good: Add column as nullable, populate data, then add constraint
def upgrade():
    # Step 1: Add nullable column
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))

    # Step 2: Set default values for existing rows
    op.execute("UPDATE users SET email_verified = false WHERE email_verified IS NULL")

    # Step 3: Make it non-nullable
    op.alter_column('users', 'email_verified', nullable=False)

def downgrade():
    op.drop_column('users', 'email_verified')
```

## CI/CD Integration

Migrations are automatically applied in our deployment pipeline:

- **Development**: Applied on `docker-compose up`
- **Staging**: Applied via Coolify on `dev` branch push
- **Production**: Applied via Coolify on version tag release

The `scripts/prestart.sh` script runs migrations before starting the FastAPI application.

## Troubleshooting

### Migration Conflicts

If you encounter "Multiple head revisions are present":

```bash
# Merge the heads
uv run alembic merge heads -m "Merge migration branches"
```

### Out of Sync Database

If your database schema doesn't match the migration history:

```bash
# Check current state
uv run alembic current

# If needed, stamp the database with a specific revision
uv run alembic stamp head
```

### Reset Everything (Development Only)

```bash
# Drop all tables and reapply migrations
docker-compose down -v
docker-compose up -d
```

## Learn More

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [FastAPI with Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## Project-Specific Notes

- Migrations use [SQLModel](https://sqlmodel.tiangolo.com/) (built on SQLAlchemy) for ORM
- Database: [PostgreSQL](https://www.postgresql.org/) 17.6
- Connection configured in `app/core/config.py`
- Migration environment setup in `env.py`
- Pre-start script: `scripts/prestart.sh` (runs migrations before app starts)
