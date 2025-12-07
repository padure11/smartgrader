"""
Diagnostic tool - shows exact database state vs migration state
"""

import os
import sys
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    sys.exit(1)

print("="*70)
print("MIGRATION DIAGNOSTIC")
print("="*70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check migration records
print("\n1. MIGRATION RECORDS in django_migrations table:")
print("-"*70)
cursor.execute("SELECT id, app, name, applied FROM django_migrations WHERE app = 'accounts' ORDER BY id")
migrations = cursor.fetchall()

if not migrations:
    print("  ⚠️  NO MIGRATIONS FOUND!")
else:
    for mid, app, name, applied in migrations:
        print(f"  [{mid:2d}] {name}")
        print(f"       Applied: {applied}")

# Check actual schema
print("\n2. ACTUAL DATABASE SCHEMA:")
print("-"*70)

print("\naccounts_test table:")
cursor.execute("PRAGMA table_info(accounts_test)")
for col in cursor.fetchall():
    print(f"  - {col[1]:20s} {col[2]}")

print("\naccounts_submission table:")
cursor.execute("PRAGMA table_info(accounts_submission)")
for col in cursor.fetchall():
    print(f"  - {col[1]:20s} {col[2]}")

print("\naccounts_testenrollment table:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_testenrollment'")
if cursor.fetchone():
    print("  ✓ Table EXISTS")
    cursor.execute("PRAGMA table_info(accounts_testenrollment)")
    for col in cursor.fetchall():
        print(f"  - {col[1]:20s} {col[2]}")
else:
    print("  ✗ Table DOES NOT EXIST")

# Check for problematic columns
print("\n3. PROBLEM DETECTION:")
print("-"*70)

cursor.execute("PRAGMA table_info(accounts_submission)")
submission_cols = {col[1] for col in cursor.fetchall()}

problems = []

if 'student_user_id' in submission_cols:
    print("  ⚠️  student_user_id column EXISTS in accounts_submission")
    # Check if migration 0005 is recorded
    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE name = '0005_test_enrollment_code_testenrollment_and_more'")
    if cursor.fetchone()[0] == 0:
        problems.append("Column exists but migration not recorded")
        print("      BUT migration 0005 is NOT in migration records!")
    else:
        print("      Migration 0005 IS recorded (this is correct)")
else:
    print("  ✓ student_user_id column does NOT exist")
    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE name = '0005_test_enrollment_code_testenrollment_and_more'")
    if cursor.fetchone()[0] > 0:
        problems.append("Migration recorded but column doesn't exist")
        print("      BUT migration 0005 IS recorded (inconsistent!)")

# Check for ghost migrations
print("\n4. GHOST MIGRATION CHECK:")
print("-"*70)
cursor.execute("SELECT name FROM django_migrations WHERE app = 'accounts' AND name LIKE '%0005%'")
all_0005 = cursor.fetchall()

if len(all_0005) > 1:
    print(f"  ⚠️  FOUND {len(all_0005)} different 0005 migrations:")
    for name, in all_0005:
        print(f"      - {name}")
    problems.append("Multiple 0005 migrations")
elif len(all_0005) == 1:
    print(f"  Single 0005 migration: {all_0005[0][0]}")
else:
    print("  No 0005 migrations recorded")

conn.close()

print("\n" + "="*70)
if problems:
    print("PROBLEMS DETECTED:")
    for p in problems:
        print(f"  ❌ {p}")
    print("\n💡 SOLUTION: Run reset_migrations.py to fix")
else:
    print("✓ No obvious problems detected")
print("="*70)
