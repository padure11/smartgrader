#!/bin/bash

# Navigate to the Django project directory
cd /home/user/smartgrader/smartgrader_app

echo "Running database migrations for student enrollment system..."
echo ""

# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations
python manage.py migrate

echo ""
echo "Migrations complete! You can now:"
echo "1. Register as a Teacher or Student"
echo "2. Teachers can create tests and share enrollment codes"
echo "3. Students can enroll using codes and view results"
