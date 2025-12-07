"""
Complete database setup - creates ALL required tables
"""

import os
import sys
import subprocess

print("="*70)
print("COMPLETE DATABASE SETUP")
print("="*70)

# Change to the Django project directory
project_dir = os.path.join(os.path.dirname(__file__), 'smartgrader_app')
os.chdir(project_dir)

print(f"\nWorking directory: {os.getcwd()}")
print("\n" + "-"*70)
print("Step 1: Running migrations for ALL Django apps")
print("-"*70)

# Run migrate with --fake for all apps
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', '--fake'],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

if result.returncode != 0:
    print("\n❌ Migration failed!")
    print("\nTrying without --fake flag...")

    # Try without fake
    result = subprocess.run(
        [sys.executable, 'manage.py', 'migrate'],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print("\n❌ Still failed. You may need to delete db.sqlite3 and start fresh.")
        sys.exit(1)

print("\n" + "-"*70)
print("Step 2: Verifying database tables")
print("-"*70)

import sqlite3
db_path = 'db.sqlite3'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check for important tables
    tables_to_check = [
        'django_session',
        'accounts_customuser',
        'accounts_profile',
        'accounts_test',
        'accounts_submission',
        'accounts_testenrollment',
    ]

    print("\nChecking for required tables:")
    all_good = True

    for table in tables_to_check:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cursor.fetchone() is not None
        status = "✓" if exists else "✗"
        print(f"  {status} {table}")
        if not exists:
            all_good = False

    conn.close()

    if all_good:
        print("\n" + "="*70)
        print("✅ DATABASE SETUP COMPLETE!")
        print("="*70)
        print("\nYou can now:")
        print("  1. Run the development server")
        print("  2. Register new accounts with Teacher/Student roles")
        print("  3. Use the student enrollment system")
    else:
        print("\n⚠️  Some tables are missing. Try deleting db.sqlite3 and running again.")
else:
    print("\n❌ Database file not found!")

print("="*70)
