"""
Check user roles in the database
"""

import os
import sys
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    sys.exit(1)

print("="*70)
print("USER ROLES CHECK")
print("="*70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if profiles table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_profile'")
if not cursor.fetchone():
    print("\n❌ accounts_profile table doesn't exist!")
    print("   Run: python manage.py migrate")
    conn.close()
    sys.exit(1)

# Get all users with their profiles
cursor.execute("""
    SELECT
        u.id,
        u.email,
        p.role,
        u.date_joined
    FROM accounts_customuser u
    LEFT JOIN accounts_profile p ON u.id = p.user_id
    ORDER BY u.date_joined DESC
""")

users = cursor.fetchall()

if not users:
    print("\n📭 No users found in database")
else:
    print(f"\n👥 Found {len(users)} user(s):\n")
    print(f"{'ID':<5} {'Email':<30} {'Role':<10} {'Joined'}")
    print("-"*70)

    for user_id, email, role, joined in users:
        role_display = role if role else "❌ NO PROFILE"
        print(f"{user_id:<5} {email:<30} {role_display:<10} {joined}")

conn.close()

print("\n" + "="*70)
print("\nTo change a user's role manually:")
print("  python manage.py shell")
print("  >>> from accounts.models import Profile")
print("  >>> profile = Profile.objects.get(user__email='your@email.com')")
print("  >>> profile.role = 'teacher'")
print("  >>> profile.save()")
print("="*70)
