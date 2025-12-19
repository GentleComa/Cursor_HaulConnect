"""
HaulConnect Flask Extensions

Initializes Flask extensions without binding to a specific application instance.
Extensions are bound to the app in the application factory.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()

