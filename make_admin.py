"""
Promote a user to admin.

Usage:
    python make_admin.py                    # promotes the first registered user
    python make_admin.py user@example.com   # promotes a specific user by email
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.database import engine, get_db, Base
from src.models import User

Base.metadata.create_all(bind=engine)

db = next(get_db())

try:
    if len(sys.argv) > 1:
        email = sys.argv[1].lower().strip()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ No user found with email: {email}")
            sys.exit(1)
    else:
        user = db.query(User).order_by(User.id).first()
        if not user:
            print("❌ No users in the database yet. Register first, then run this script.")
            sys.exit(1)

    if user.is_admin:
        print(f"ℹ️  User '{user.email}' is already an admin.")
    else:
        user.is_admin = 1
        db.commit()
        print(f"✅ User '{user.email}' (ID #{user.id}) promoted to admin!")

    # Show all admins
    admins = db.query(User).filter(User.is_admin == 1).all()
    print(f"\nCurrent admins ({len(admins)}):")
    for a in admins:
        print(f"  • {a.email} (ID #{a.id})")

finally:
    db.close()
