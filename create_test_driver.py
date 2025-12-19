#!/usr/bin/env python
"""
Quick script to create test driver user.
Run this from the project root with: python create_test_driver.py
"""

from app import create_app
from extensions import db
from models.user import User

app = create_app()

with app.app_context():
    # Check if driver already exists
    driver = User.query.filter_by(email='driver@test.com').first()
    
    if driver:
        print(f"Driver user already exists: {driver.email}")
        print(f"Username: {driver.username}")
        print(f"Role: {driver.role}")
    else:
        # Create driver user
        driver = User(
            email='driver@test.com',
            username='testdriver',
            first_name='Test',
            last_name='Driver',
            role='driver',
            mc_number='MC123456',
            equipment_type='dry_van',
            is_verified=True,
            is_active=True
        )
        driver.set_password('password123')
        db.session.add(driver)
        db.session.commit()
        print("✓ Test driver user created successfully!")
        print(f"  Email: driver@test.com")
        print(f"  Password: password123")
        print(f"  MC Number: MC123456")
        print(f"  Equipment: dry_van")
    
    print("\nYou can now log in at: http://localhost:5001/auth/login")

