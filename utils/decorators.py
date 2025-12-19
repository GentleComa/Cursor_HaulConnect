"""
Utility Decorators

Role-based access control and other decorators.
"""

from functools import wraps
from flask import abort, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Decorator to require specific user roles.
    
    Usage:
        @role_required('shipper', 'broker')
        def my_route():
            ...
    
    Args:
        *roles: One or more role names that are allowed
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Check if user has one of the required roles
            user_role = current_user.role
            if user_role not in roles:
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

