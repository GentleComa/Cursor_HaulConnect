"""
User Model

Defines the User model for authentication and user management.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from extensions import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication and profile management."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for passwordless auth mode
    
    # Profile fields
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(128))
    
    # Role: 'driver', 'dispatcher', 'broker', 'shipper', 'admin'
    role = db.Column(db.String(20), default='driver')
    
    # Driver-specific fields
    mc_number = db.Column(db.String(20))
    dot_number = db.Column(db.String(20))
    equipment_type = db.Column(db.String(50))  # dry_van, flatbed, reefer, etc.
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)  # Admin access flag
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    posted_loads = db.relationship('Load', foreign_keys='Load.shipper_id', backref='shipper', lazy='dynamic')
    assigned_loads = db.relationship('Load', foreign_keys='Load.driver_id', backref='driver', lazy='dynamic')
    payments_received = db.relationship('Payment', foreign_keys='Payment.driver_id', backref='driver', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set the user's password."""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None
    
    def check_password(self, password, allow_passwordless=False):
        """
        Verify password against stored hash.
        
        Args:
            password: The password to check
            allow_passwordless: If True, allows authentication when password_hash is None
                              (for passwordless dev mode). Defaults to False for security.
        
        Returns:
            True if password matches or if passwordless mode is allowed and hash is None,
            False otherwise
        """
        if self.password_hash is None:
            # Only allow passwordless authentication if explicitly permitted
            # This prevents users created in passwordless mode from authenticating
            # when AUTH_PASSWORD_REQUIRED is True
            return allow_passwordless
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.username
    
    def is_driver(self):
        return self.role == 'driver'
    
    def is_shipper(self):
        return self.role in ['shipper', 'broker']
    
    def has_admin_access(self):
        """Check if user has admin access (either by is_admin flag or admin role)."""
        # Access the column value directly using getattr to avoid recursion
        is_admin_flag = getattr(self, 'is_admin', False)
        return is_admin_flag or self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    if user_id is None:
        return None
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

