"""
HaulConnect Application Entry Point

Run this file to start the Flask development server:
    python app.py

For production, use a WSGI server like Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
"""

import os
from flask import Flask, render_template

from config import config
from extensions import db, login_manager, csrf


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Configuration to use ('development', 'testing', 'production')
                    Defaults to FLASK_ENV environment variable or 'development'
    
    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create Flask app instance
    app = Flask(__name__)
    
    # Load configuration
    config_class = config[config_name]
    app.config.from_object(config_class)
    
    # Call config-specific initialization (e.g., production security checks)
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Import models to register them with SQLAlchemy
    import models  # noqa: F401
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Add template context processor to make config available in templates
    @app.context_processor
    def inject_config():
        return dict(config=app.config)
    
    # Create database tables
    with app.app_context():
        # Ensure instance directory exists for SQLite
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri[10:]  # Remove 'sqlite:///'
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        db.create_all()
    
    return app


def register_error_handlers(app):
    """Register custom error handlers."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403


# Create application instance (for WSGI servers)
app = create_app()

if __name__ == '__main__':
    # Use port from environment variable or default to 5001 (5000 is often used by AirPlay on macOS)
    port = int(os.environ.get('PORT', 5001))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )
