"""
Fix user role - change a user from student to teacher or vice versa
"""

import os
import sys
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'smartgrader_app', 'db.sqlite3')

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    sys.exit(1)

print("="*70)
print("FIX USER ROLE")
print("="*70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all users
cursor.execute("""
    SELECT
        u.id,
        u.email,
        p.id as profile_id,
        p.role
    FROM accounts_customuser u
    LEFT JOIN accounts_profile p ON u.id = p.user_id
    ORDER BY u.date_joined DESC
""")

users = cursor.fetchall()

if not users:
    print("\n📭 No users found in database")
    conn.close()
    sys.exit(0)

print(f"\n👥 Available users:\n")
for i, (user_id, email, profile_id, role) in enumerate(users, 1):
    role_display = role if role else "NO PROFILE"
    print(f"  [{i}] {email} (currently: {role_display})")

print("\n" + "-"*70)

try:
    choice = input("\nEnter user number to update (or 'q' to quit): ").strip()

    if choice.lower() == 'q':
        print("Cancelled.")
        conn.close()
        sys.exit(0)

    choice = int(choice)
    if choice < 1 or choice > len(users):
        print("Invalid choice.")
        conn.close()
        sys.exit(1)

    user_id, email, profile_id, current_role = users[choice - 1]

    print(f"\nSelected user: {email}")
    print(f"Current role: {current_role}")

    print("\nAvailable roles:")
    print("  [1] teacher")
    print("  [2] student")

    role_choice = input("\nEnter new role number: ").strip()

    new_role = None
    if role_choice == '1':
        new_role = 'teacher'
    elif role_choice == '2':
        new_role = 'student'
    else:
        print("Invalid role choice.")
        conn.close()
        sys.exit(1)

    if new_role == current_role:
        print(f"\nUser already has role '{new_role}'. No changes needed.")
    else:
        # Update the role
        if profile_id:
            cursor.execute("UPDATE accounts_profile SET role = ? WHERE id = ?", (new_role, profile_id))
        else:
            cursor.execute("INSERT INTO accounts_profile (user_id, role) VALUES (?, ?)", (user_id, new_role))

        conn.commit()
        print(f"\n✅ Successfully updated {email} to role '{new_role}'")

        if new_role == 'teacher':
            print("\n🎓 This user will now see:")
            print("   - Create Test")
            print("   - My Tests (teacher view)")
        else:
            print("\n📚 This user will now see:")
            print("   - My Tests (student dashboard)")
            print("   - Enrollment form")

except ValueError:
    print("Invalid input.")
except KeyboardInterrupt:
    print("\nCancelled.")
finally:
    conn.close()

print("\n" + "="*70)
