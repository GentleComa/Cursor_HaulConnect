#!/usr/bin/env python
"""
Quick script to create test admin user.
Run this from the project root with: python create_admin.py
"""

from app import create_app
from extensions import db
from models.user import User

app = create_app()

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(email='admin@test.com').first()
    
    if admin:
        print(f"Admin user already exists: {admin.email}")
        print(f"Username: {admin.username}")
        print(f"Role: {admin.role}")
        print(f"is_admin flag: {admin.is_admin}")
        # Ensure is_admin flag is set
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print("✓ Updated is_admin flag to True")
    else:
        # Create admin user
        admin = User(
            email='admin@test.com',
            username='testadmin',
            first_name='Test',
            last_name='Admin',
            role='admin',
            is_admin=True,  # Set admin flag
            is_verified=True,
            is_active=True
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created successfully!")
        print(f"  Email: admin@test.com")
        print(f"  Password: password123")
    
    print("\nYou can now log in at: http://localhost:5001/auth/login")

