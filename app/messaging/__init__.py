"""
Messaging Blueprint

Handles internal messaging between users (drivers, dispatchers, etc.)
"""

from flask import Blueprint

messaging_bp = Blueprint('messaging', __name__)

from app.messaging import routes  # noqa: F401, E402

