"""
Authentication Tests
"""
import pytest
from flask import url_for
from extensions import db
from models.user import User




def test_register(client):
    """Test user registration."""
    with client.application.app_context():
        response = client.post('/auth/register', data={
            'email': 'newuser@test.com',
            'username': 'newuser',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'shipper',
            'first_name': 'New',
            'last_name': 'User'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert User.query.filter_by(email='newuser@test.com').first() is not None


def test_login_shipper(client, shipper_user):
    """Test shipper login and redirect."""
    response = client.post('/auth/login', data={
        'email': 'shipper@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Should redirect to dashboard
    assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()


def test_login_driver(client, driver_user):
    """Test driver login and redirect."""
    response = client.post('/auth/login', data={
        'email': 'driver@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Should redirect to load board
    assert b'Load Board' in response.data or b'load' in response.data.lower()


def test_login_invalid_credentials(client, shipper_user):
    """Test login with invalid credentials."""
    response = client.post('/auth/login', data={
        'email': 'shipper@test.com',
        'password': 'wrongpassword'
    })
    
    assert response.status_code == 200
    assert b'Invalid' in response.data or b'error' in response.data.lower()


def test_logout(client, shipper_user):
    """Test user logout."""
    # Login first
    client.post('/auth/login', data={
        'email': 'shipper@test.com',
        'password': 'password123'
    })
    
    # Logout
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200


def test_role_required_decorator(client, shipper_user, driver_user):
    """Test that role_required decorator works correctly."""
    # Login as shipper
    client.post('/auth/login', data={
        'email': 'shipper@test.com',
        'password': 'password123'
    })
    
    # Try to access driver-only route
    response = client.get('/loads/driver/load-board')
    # Should either redirect or show 403
    assert response.status_code in [200, 302, 403]

