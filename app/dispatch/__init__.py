"""
Dispatch Blueprint

Handles load dispatch operations: load management, assignments, tracking.
"""

from flask import Blueprint

dispatch_bp = Blueprint('dispatch', __name__)

from app.dispatch import routes  # noqa: F401, E402

