# Database migrations

This project uses Alembic with SQLAlchemy metadata. Apply migrations from the repository root with:

```powershell
python -m alembic upgrade head
```

Set `DATABASE_URL` in `.env` first. Keep future migrations additive and numbered; do not edit an applied migration. Do not run downgrade commands against a shared or production database without an explicit backup and approval.
