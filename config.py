"""
HaulConnect Configuration Module

Loads configuration from environment variables using python-dotenv.
Supports multiple environments: development, testing, production.
"""

import os
import secrets
import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_secret_key():
    """
    Get SECRET_KEY from environment variables or generate a strong random one.
    
    Returns:
        str: Secret key from environment or a randomly generated one
    """
    secret_key = os.getenv("SECRET_KEY") or os.getenv("SESSION_SECRET")
    
    if not secret_key:
        # Generate a strong random secret key (32 bytes = 256 bits)
        secret_key = secrets.token_urlsafe(32)
        warnings.warn(
            "SECRET_KEY not set in environment. Generated a random key for this session. "
            "This key will change on each restart. Set SECRET_KEY or SESSION_SECRET in "
            "your environment for a persistent key.",
            UserWarning
        )
    
    return secret_key


def _normalize_sqlite_path(database_url):
    """
    Normalize SQLite database paths to use instance/ directory (Flask convention).
    
    This function implements Alternative 1: Automatic normalization.
    It converts root-level SQLite paths (e.g., "sqlite:///file.db") to 
    instance directory paths (e.g., "sqlite:///instance/file.db").
    
    Args:
        database_url: Database URL string
        
    Returns:
        str: Normalized database URL
    """
    if not database_url or not database_url.startswith('sqlite:///'):
        return database_url
    
    # Extract the path part after sqlite:///
    path_part = database_url[10:]  # Remove "sqlite:///"
    
    # If path doesn't start with instance/, check if it's a root-level file
    if not path_part.startswith('instance/'):
        # Check if it's a simple filename (root-level)
        if '/' not in path_part and path_part.endswith('.db'):
            # Normalize to instance/ directory
            normalized = f"sqlite:///instance/{path_part}"
            warnings.warn(
                f"Database path normalized from '{database_url}' to '{normalized}'. "
                f"Update .env DATABASE_URL to 'sqlite:///instance/{path_part}' to avoid this warning.",
                UserWarning
            )
            return normalized
    
    return database_url


class Config:
    """Base configuration class with shared settings."""
    
    # Security
    # Generate a strong random key if none is provided (development/testing only)
    # Production enforces explicit configuration via init_app()
    SECRET_KEY = _get_secret_key()
    
    # Database
    # Support both DATABASE_URL and SQLITE_DATABASE_URL for compatibility
    # Default uses instance/ directory (Flask convention) to keep database files separate
    # Alternative 1: Automatic normalization - converts root-level SQLite paths to instance/
    _raw_db_url = os.getenv("DATABASE_URL") or os.getenv("SQLITE_DATABASE_URL", "sqlite:///instance/haulconnect.db")
    _normalized_url = _normalize_sqlite_path(_raw_db_url)
    # Convert to absolute path to handle spaces in directory names
    if _normalized_url.startswith('sqlite:///'):
        db_path = _normalized_url[10:]  # Remove 'sqlite:///'
        if not os.path.isabs(db_path):
            # Make path absolute to avoid issues with spaces in directory names
            import os as os_module
            abs_db_path = os_module.path.abspath(db_path)
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{abs_db_path}"
        else:
            SQLALCHEMY_DATABASE_URI = _normalized_url
    else:
        SQLALCHEMY_DATABASE_URI = _normalized_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # Authentication
    # Passwordless mode: Set to False to allow registration/login without passwords (DEV/TEST ONLY)
    AUTH_PASSWORD_REQUIRED = os.getenv("AUTH_PASSWORD_REQUIRED", "true").lower() == "true"
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Pagination
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries
    
    # Require passwords in development (can be overridden via env var)
    # Set to "false" in env var if you want passwordless mode for testing
    AUTH_PASSWORD_REQUIRED = os.getenv("AUTH_PASSWORD_REQUIRED", "true").lower() == "true"


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Allow passwordless auth in testing (can be overridden via env var)
    AUTH_PASSWORD_REQUIRED = os.getenv("AUTH_PASSWORD_REQUIRED", "false").lower() == "true"


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    
    # Always require passwords in production (security)
    AUTH_PASSWORD_REQUIRED = True
    
    # In production, SECRET_KEY must be set via environment variable
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        assert os.getenv('SECRET_KEY') or os.getenv('SESSION_SECRET'), \
            'SECRET_KEY or SESSION_SECRET environment variable must be set'
        # Ensure passwordless mode is never enabled in production
        assert app.config.get('AUTH_PASSWORD_REQUIRED', True), \
            'AUTH_PASSWORD_REQUIRED must be True in production'


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

