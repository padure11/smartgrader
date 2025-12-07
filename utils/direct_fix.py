"""
Direct database fix for migration conflicts.
This script inspects the actual database state and fixes migration records.
"""

import os
import sys
import sqlite3

# Find the database file
db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    print(f"   Looking in: {os.path.dirname(__file__)}")
    sys.exit(1)

print("="*70)
print("Direct Migration Fix")
print("="*70)
print(f"Database: {db_path}\n")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Step 1: Check what columns exist in the tables
print("Step 1: Checking actual database schema...")
print("\nColumns in 'accounts_test' table:")
cursor.execute("PRAGMA table_info(accounts_test)")
test_columns = cursor.fetchall()
for col in test_columns:
    print(f"  - {col[1]} ({col[2]})")

has_enrollment_code = any(col[1] == 'enrollment_code' for col in test_columns)

print("\nColumns in 'accounts_submission' table:")
cursor.execute("PRAGMA table_info(accounts_submission)")
submission_columns = cursor.fetchall()
for col in submission_columns:
    print(f"  - {col[1]} ({col[2]})")

has_student_user_id = any(col[1] == 'student_user_id' for col in submission_columns)

# Step 2: Check if TestEnrollment table exists
print("\nChecking for 'accounts_testenrollment' table:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_testenrollment'")
has_enrollment_table = cursor.fetchone() is not None
print(f"  {'✓ EXISTS' if has_enrollment_table else '✗ DOES NOT EXIST'}")

# Step 3: Check migration records
print("\nStep 2: Checking migration records...")
cursor.execute("SELECT id, app, name FROM django_migrations WHERE app = 'accounts' ORDER BY id")
migrations = cursor.fetchall()

print("\nApplied migrations:")
for mid, app, name in migrations:
    print(f"  [{mid}] {name}")

# Step 4: Determine what to do
print("\n" + "="*70)
print("Analysis:")
print("="*70)

print(f"enrollment_code column exists: {has_enrollment_code}")
print(f"student_user_id column exists: {has_student_user_id}")
print(f"accounts_testenrollment table exists: {has_enrollment_table}")

# The columns already exist, so we need to mark migrations as applied
if has_enrollment_code and has_student_user_id and has_enrollment_table:
    print("\n✓ All required database changes are already present!")
    print("  The migrations just need to be marked as applied in the database.")
    print("\nSolution: Manually insert migration records\n")

    # Check if our migrations are recorded
    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'accounts' AND name = '0005_test_enrollment_code_testenrollment_and_more'")
    has_0005 = cursor.fetchone()[0] > 0

    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'accounts' AND name = '0006_generate_enrollment_codes'")
    has_0006 = cursor.fetchone()[0] > 0

    if not has_0005:
        print("Adding migration record for 0005...")
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('accounts', '0005_test_enrollment_code_testenrollment_and_more', datetime('now'))
        """)
        print("  ✓ Added 0005")
    else:
        print("  Migration 0005 already recorded")

    if not has_0006:
        print("Adding migration record for 0006...")
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('accounts', '0006_generate_enrollment_codes', datetime('now'))
        """)
        print("  ✓ Added 0006")
    else:
        print("  Migration 0006 already recorded")

    # Remove any conflicting ghost migrations
    ghost_migrations = [
        '0005_submission_student_user_test_enrollment_code_and_more',
    ]

    for ghost in ghost_migrations:
        cursor.execute("DELETE FROM django_migrations WHERE app = 'accounts' AND name = ?", (ghost,))
        if cursor.rowcount > 0:
            print(f"  ✓ Removed ghost migration: {ghost}")

    conn.commit()
    print("\n✓ Database migration records fixed!")
    print("\nYou can now run the server. The database is ready to use.")

else:
    print("\n⚠️  Database is missing some changes.")
    print("   This script can only fix migration records, not apply schema changes.")
    print("   You may need to manually add the missing columns/tables.")

conn.close()

print("="*70)
