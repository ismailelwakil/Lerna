# Migrations

Dev: tables auto-create on startup (SQLite or any DATABASE_URL).

Production (Postgres — e.g. the configured Supabase instance):
```bash
pip install alembic psycopg2-binary
alembic init migrations/alembic
alembic revision --autogenerate -m "content module schema"
alembic upgrade head
```
Set `sqlalchemy.url` from DATABASE_URL. Models: app/db/models.py.