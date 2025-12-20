"""
Admin Panel Tests
"""
import pytest
from extensions import db
from models.user import User


def test_admin_required_decorator(client, shipper_user):
    """Test that admin routes require admin access."""
    # Login as regular shipper
    client.post('/auth/login', data={
        'email': 'shipper@test.com',
        'password': 'password123'
    })
    
    # Try to access admin route
    response = client.get('/admin/dashboard')
    assert response.status_code == 403


def test_admin_access(client):
    """Test admin can access admin routes."""
    # Create admin user
    with client.application.app_context():
        admin = User(
            email='admin@test.com',
            username='admin',
            role='admin',
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
    
    # Login as admin
    client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    })
    
    # Access admin route
    response = client.get('/admin/dashboard')
    assert response.status_code == 200


def test_admin_user_management(client):
    """Test admin can manage users."""
    # Create admin user
    with client.application.app_context():
        admin = User(
            email='admin@test.com',
            username='admin',
            role='admin',
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True
        )
        admin.set_password('password123')
        
        user = User(
            email='user@test.com',
            username='user',
            role='shipper',
            first_name='Test',
            last_name='User',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Login as admin
    client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    })
    
    # Toggle user active status
    response = client.post(f'/admin/users/{user_id}/toggle-active', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify user is deactivated
    with client.application.app_context():
        user = User.query.get(user_id)
        assert user.is_active == False

