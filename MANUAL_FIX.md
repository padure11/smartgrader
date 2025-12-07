# Manual Migration Fix

If the automatic scripts don't work, follow these steps:

## Option 1: Fake the Migrations (RECOMMENDED)

Since your database already has the required columns/tables, just mark the migrations as applied without running them:

```bash
cd smartgrader_app
python manage.py migrate accounts 0005 --fake
python manage.py migrate accounts 0006 --fake
```

This tells Django "the migrations are applied" without actually running them.

## Option 2: Delete and Recreate Database (NUCLEAR OPTION)

⚠️ WARNING: This will delete ALL your data!

```bash
cd smartgrader_app

# Delete the database
del db.sqlite3  # Windows
# rm db.sqlite3  # Linux/Mac

# Recreate from scratch
python manage.py migrate

# Create a superuser
python manage.py createsuperuser
```

## Option 3: SQL Direct Fix

Open the database with SQLite and run these commands:

```bash
cd smartgrader_app

# Open SQLite
sqlite3 db.sqlite3

# Inside SQLite:
DELETE FROM django_migrations WHERE app = 'accounts' AND name LIKE '%0005%';
DELETE FROM django_migrations WHERE app = 'accounts' AND name LIKE '%0006%';

INSERT INTO django_migrations (app, name, applied)
VALUES ('accounts', '0005_test_enrollment_code_testenrollment_and_more', datetime('now'));

INSERT INTO django_migrations (app, name, applied)
VALUES ('accounts', '0006_generate_enrollment_codes', datetime('now'));

.quit
```

Then try migrating again:
```bash
python manage.py migrate
```

## Option 4: Check Migration State

See what migrations Django thinks are applied:

```bash
python manage.py showmigrations accounts
```

Look for any migrations with `[ ]` (not applied) or `[X]` (applied).
If you see duplicate 0005 migrations, that's the problem.
