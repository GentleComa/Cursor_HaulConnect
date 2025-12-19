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


def register_routes(app: Flask):
    """Register all blueprints with the Flask application."""
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(loads_bp, url_prefix='/loads')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Only register simulate blueprint in DEBUG mode (development/testing only)
    if app.config.get('DEBUG', False):
        from routes.simulate import simulate_bp
        app.register_blueprint(simulate_bp, url_prefix='/simulate')
    
    # Root route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Debug endpoint to check DEBUG mode
    @app.route('/debug-check')
    def debug_check():
        from flask import jsonify
        import os
        return jsonify({
            'DEBUG': app.config.get('DEBUG', False),
            'FLASK_ENV': os.environ.get('FLASK_ENV', 'not set'),
            'simulate_routes_registered': 'simulate' in [bp.name for bp in app.blueprints.values()]
        })

