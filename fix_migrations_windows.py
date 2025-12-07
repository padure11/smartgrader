"""
Fix migration conflicts for Windows users.
Run this from the smartgrader directory: python fix_migrations_windows.py
"""

import os
import sys
import sqlite3

# Find the database file
db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    sys.exit(1)

print("="*70)
print("Migration Conflict Fixer for Windows")
print("="*70)
print(f"\nDatabase: {db_path}\n")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current migration status
print("Current migration status for 'accounts' app:")
cursor.execute("SELECT id, app, name, applied FROM django_migrations WHERE app = 'accounts' ORDER BY id")
migrations = cursor.fetchall()

for mid, app, name, applied in migrations:
    print(f"  [{mid}] {name}")

# Find conflicting migrations
print("\nLooking for conflicts...")

conflicting_names = [
    '0005_submission_student_user_test_enrollment_code_and_more',
]

conflicts_found = False
for name in conflicting_names:
    cursor.execute("SELECT id FROM django_migrations WHERE app = 'accounts' AND name = ?", (name,))
    result = cursor.fetchone()
    if result:
        conflicts_found = True
        print(f"  ⚠️  Found: {name} (ID: {result[0]})")

if conflicts_found:
    print("\n" + "="*70)
    response = input("Delete conflicting migrations? (yes/no): ").strip().lower()

    if response == 'yes':
        for name in conflicting_names:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'accounts' AND name = ?", (name,))
            if cursor.rowcount > 0:
                print(f"  ✓ Deleted: {name}")

        conn.commit()
        print("\n✓ Conflicts resolved!")
        print("\nNow run: python manage.py migrate")
    else:
        print("\nNo changes made.")
else:
    print("  ✓ No conflicts found!")
    print("\nYou can run: python manage.py migrate")

conn.close()

print("="*70)
