"""
HaulConnect Routes

Register all application blueprints.
"""

from flask import Flask

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.loads import loads_bp
from routes.api import api_bp
from routes.admin import admin_bp
from routes.simulate import simulate_bp


def register_routes(app: Flask):
    """Register all blueprints with the Flask application."""
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(loads_bp, url_prefix='/loads')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(simulate_bp, url_prefix='/simulate')
    
    # Root route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

