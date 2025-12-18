"""
HaulConnect Application Factory

Creates and configures the Flask application instance.
"""

import os
from flask import Flask, render_template

from config import config
from extensions import db, migrate, login_manager, csrf


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
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Import models to register them with SQLAlchemy and Flask-Login
    # This must happen before db.create_all() so tables are created,
    # and registers the @login_manager.user_loader callback
    from app import models  # noqa: F401
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def register_blueprints(app):
    """Register all application blueprints."""
    
    from app.auth import auth_bp
    from app.messaging import messaging_bp
    from app.dispatch import dispatch_bp
    from app.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    app.register_blueprint(dispatch_bp, url_prefix='/dispatch')


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

