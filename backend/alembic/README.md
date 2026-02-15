# Alembic Migration Scripts

This directory contains database migration scripts managed by Alembic.

## Running Migrations

### Upgrade to latest version
```bash
alembic upgrade head
```

### Downgrade one version
```bash
alembic downgrade -1
```

### Create new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

## Migration Files

Migrations are stored in the `versions/` subdirectory.
