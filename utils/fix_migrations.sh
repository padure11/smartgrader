#!/bin/bash

echo "========================================"
echo "Migration Conflict Fixer"
echo "========================================"
echo ""

cd /home/user/smartgrader/smartgrader_app || exit 1

# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Step 1: Checking current migration status..."
python manage.py showmigrations accounts

echo ""
echo "Step 2: Rolling back the conflicting migration..."
echo "This will unapply migration 0005 that's causing the conflict"

# Rollback to migration 0004
python manage.py migrate accounts 0004 --fake

echo ""
echo "Step 3: Clearing migration history for problematic migrations..."

# Use Python to access Django ORM and clean up migration records
python << 'PYTHON_SCRIPT'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartgrader_app.settings')
django.setup()

from django.db import connection

# Delete any migration records that might be conflicting
cursor = connection.cursor()
cursor.execute("""
    DELETE FROM django_migrations
    WHERE app = 'accounts'
    AND name LIKE '0005%'
""")
cursor.execute("""
    DELETE FROM django_migrations
    WHERE app = 'accounts'
    AND name LIKE '0006%'
""")
connection.commit()
print("Cleared conflicting migration records")
PYTHON_SCRIPT

echo ""
echo "Step 4: Re-applying migrations..."
python manage.py migrate

echo ""
echo "========================================"
echo "Migration fix complete!"
echo "========================================"
