"""
Application Tests

Basic tests to verify the app is working.
"""


def test_app_exists(app):
    """Test that the app exists."""
    assert app is not None


def test_app_is_testing(app):
    """Test that the app is in testing mode."""
    assert app.config['TESTING'] is True


def test_index_page(client):
    """Test that the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'HaulConnect' in response.data


def test_login_page(client):
    """Test that the login page loads."""
    response = client.get('/auth/login')
    assert response.status_code == 200


def test_register_page(client):
    """Test that the register page loads."""
    response = client.get('/auth/register')
    assert response.status_code == 200

