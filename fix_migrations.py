#!/usr/bin/env python
"""
Fix migration conflicts for student portal system.
This script handles the case where migrations were partially applied.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smartgrader_app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartgrader_app.settings')
django.setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

def fix_migrations():
    """Fix migration conflicts by cleaning up and reapplying"""

    print("Checking migration status...")

    # Get the migration recorder
    recorder = MigrationRecorder(connection)

    # Get all applied migrations for accounts app
    applied = recorder.applied_migrations()
    accounts_migrations = [m for m in applied if m[0] == 'accounts']

    print(f"\nCurrently applied migrations for 'accounts' app:")
    for app, name in sorted(accounts_migrations):
        print(f"  - {name}")

    # Check for conflicting migration
    conflicting_migrations = [
        ('accounts', '0005_submission_student_user_test_enrollment_code_and_more'),
    ]

    conflicts_found = False
    for migration in conflicting_migrations:
        if migration in applied:
            conflicts_found = True
            print(f"\n⚠️  Found conflicting migration: {migration[1]}")
            print(f"   Removing it from migration history...")
            recorder.record_unapplied(migration[0], migration[1])
            print(f"   ✓ Removed")

    if not conflicts_found:
        print("\n✓ No migration conflicts found")

    # Check if our migrations are already applied
    our_migrations = [
        ('accounts', '0005_test_enrollment_code_testenrollment_and_more'),
        ('accounts', '0006_generate_enrollment_codes'),
    ]

    print("\nChecking if new migrations need to be applied...")
    for migration in our_migrations:
        if migration not in applied:
            print(f"  Migration {migration[1]} needs to be applied")
        else:
            print(f"  ✓ Migration {migration[1]} already applied")

    print("\n" + "="*70)
    if conflicts_found:
        print("Conflicts resolved! Now run: python manage.py migrate")
    else:
        print("No conflicts. You can run: python manage.py migrate")
    print("="*70)

if __name__ == '__main__':
    try:
        fix_migrations()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
