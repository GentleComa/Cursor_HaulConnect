"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import pytest
import sys
import os

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
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()

