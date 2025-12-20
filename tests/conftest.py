"""
Pytest Configuration and Fixtures
"""
import pytest
import os
import tempfile

# Import create_app from app.py module (not app/ package)
# The app/ directory shadows app.py, so we use importlib
import importlib.util

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("app_module", os.path.join(project_root, "app.py"))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
create_app = app_module.create_app
from extensions import db


@pytest.fixture
def app():
    """Create application for testing."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Create app with 'testing' config, then override specific values
    app = create_app('testing')
    
    # Override configuration for test-specific settings
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['AUTH_PASSWORD_REQUIRED'] = True
    app.config['DEBUG'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def shipper_user(app):
    """Create a test shipper user."""
    with app.app_context():
        from models.user import User
        user = User(
            email='shipper@test.com',
            username='test_shipper',
            role='shipper',
            first_name='Test',
            last_name='Shipper',
            company_name='Test Co',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def driver_user(app):
    """Create a test driver user."""
    with app.app_context():
        from models.user import User
        user = User(
            email='driver@test.com',
            username='test_driver',
            role='driver',
            first_name='Test',
            last_name='Driver',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user
