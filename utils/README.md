# SmartGrader Utility Scripts

This folder contains utility scripts for managing the SmartGrader application.

## Migration Tools

### `run_migrations.sh` (Linux/Mac)
**Use when:** Setting up the database for the first time
```bash
bash utils/run_migrations.sh
```
- Activates virtual environment
- Runs Django migrations
- Sets up all required tables

### `fix_migrations_windows.py` (Windows - Recommended)
**Use when:** Migration conflicts (duplicate column errors)
```bash
python utils/fix_migrations_windows.py
```
- Detects conflicting migrations in SQLite database
- Removes ghost migration records
- Interactive confirmation before changes

### `diagnose.py`
**Use when:** Diagnosing migration or database issues
```bash
python utils/diagnose.py
```
- Shows migration records in database
- Displays actual database schema
- Identifies inconsistencies
- No modifications made (read-only)

### `reset_migrations.py`
**Use when:** Complete migration reset needed
```bash
python utils/reset_migrations.py
```
- Removes ALL migration records for accounts app
- Re-adds them in correct order
- Nuclear option for fixing migration conflicts
- **Warning:** Only touches migration records, not data

### `direct_fix.py`
**Use when:** Auto-fixing migration records
```bash
python utils/direct_fix.py
```
- Checks actual database state
- Adds missing migration records
- Removes conflicting records
- Fully automated fix

### `fix_migrations.sh` / `fix_migrations.py`
Alternative migration fix tools (older versions)

### `cleanup_migrations.py`
**Use when:** Finding duplicate migration files
```bash
python utils/cleanup_migrations.py
python utils/cleanup_migrations.py --delete  # to remove
```
- Scans for duplicate/unexpected migration files
- Can auto-delete with --delete flag

### `complete_setup.py`
**Use when:** Complete database setup
```bash
python utils/complete_setup.py
```
- Runs migrations with --fake
- Verifies all tables exist
- Provides detailed feedback

---

## User Management Tools

### `fix_user_role.py` ⭐
**Use when:** Need to change a user's role (student ↔ teacher)
```bash
python utils/fix_user_role.py
```
- Interactive script
- Lists all users with current roles
- Allows selecting and changing roles
- Updates database directly

### `check_user_role.py`
**Use when:** Checking what roles users have
```bash
python utils/check_user_role.py
```
- Displays all users and their roles
- Shows users without profiles
- Read-only (no modifications)

---

## Student Matching Tools

### `match_students.py` ⭐
**Use when:** Students can't see their graded tests
```bash
python utils/match_students.py
```
- Matches unlinked submissions to enrolled students
- Based on name matching (case-insensitive)
- Handles name variations and swaps
- Shows summary of matched vs unmatched

---

## Fix Guides (Text Files)

### `FINAL_FIX.txt`
Step-by-step guide for:
- Creating missing Django tables (django_session, etc.)
- Fixing profile race conditions
- Using --run-syncdb flag

### `MANUAL_FIX.md`
Manual solutions for migration conflicts:
- Using --fake flag
- Nuclear option (delete db)
- Direct SQL commands
- Diagnosis commands

### `QUICK_FIX.txt`
Quick reference for common fixes:
- Using --fake for migrations
- Checking for duplicate files
- Nuclear reset option

---

## Common Workflows

### First Time Setup
```bash
cd smartgrader
bash utils/run_migrations.sh
```

### Migration Conflicts (Windows)
```bash
python utils/diagnose.py          # See what's wrong
python utils/fix_migrations_windows.py  # Fix it
cd smartgrader_app
python manage.py migrate
```

### Students Can't See Graded Tests
```bash
python utils/match_students.py
```

### Change User Role
```bash
python utils/fix_user_role.py
```

---

## Notes

- Most scripts automatically detect the database location
- Scripts use Django ORM when possible (safe)
- Some scripts modify SQLite database directly (clearly documented)
- Always shows what changes will be made before applying
- Can be run from project root directory

---

## Script Dependencies

All scripts require:
- Python 3.x
- Django installed (automatically imports from smartgrader_app)
- SQLite database exists at `smartgrader_app/db.sqlite3`

Migration scripts work with the existing migration files in:
`smartgrader_app/accounts/migrations/`
