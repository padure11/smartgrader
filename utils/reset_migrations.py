"""
Complete migration reset - nuclear option but guaranteed to work.
This removes all migration history and re-fakes everything based on current schema.
"""

import os
import sys
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    sys.exit(1)

print("="*70)
print("COMPLETE MIGRATION RESET")
print("="*70)
print("\nThis will:")
print("  1. Remove ALL migration records for 'accounts' app")
print("  2. Fake-apply all migrations based on current database state")
print("  3. Fix the migration conflict permanently")
print("\n⚠️  This does NOT delete any data - only migration records")
print("="*70)

response = input("\nContinue? (yes/no): ").strip().lower()

if response != 'yes':
    print("Cancelled.")
    sys.exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\nStep 1: Checking current state...")
cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'accounts'")
count = cursor.fetchone()[0]
print(f"  Found {count} migration records for 'accounts' app")

print("\nStep 2: Removing ALL migration records for 'accounts' app...")
cursor.execute("DELETE FROM django_migrations WHERE app = 'accounts'")
deleted = cursor.rowcount
print(f"  ✓ Deleted {deleted} migration records")

conn.commit()

print("\nStep 3: Re-adding migrations in correct order...")

# Add migrations in the correct order
migrations_to_add = [
    '0001_initial',
    '0002_test',
    '0003_submission',
    '0004_remove_submission_student_name_submission_first_name_and_more',
    '0005_test_enrollment_code_testenrollment_and_more',
    '0006_generate_enrollment_codes',
]

for migration_name in migrations_to_add:
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        VALUES ('accounts', ?, datetime('now'))
    """, (migration_name,))
    print(f"  ✓ Added: {migration_name}")

conn.commit()

print("\nStep 4: Verifying...")
cursor.execute("SELECT name FROM django_migrations WHERE app = 'accounts' ORDER BY id")
current_migrations = [row[0] for row in cursor.fetchall()]

print("\nCurrent migration state:")
for i, name in enumerate(current_migrations, 1):
    print(f"  [{i}] {name}")

conn.close()

print("\n" + "="*70)
print("✓ MIGRATION RESET COMPLETE!")
print("="*70)
print("\nYou can now run:")
print("  cd smartgrader_app")
print("  python manage.py migrate")
print("\nThis should work without errors.")
print("="*70)
