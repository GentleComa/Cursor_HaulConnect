"""
Main Routes

Core application routes for home and dashboard.
"""

from flask import render_template
from app.main import main_bp


@main_bp.route('/')
def index():
    """Landing page."""
    return render_template('main/index.html')


@main_bp.route('/dashboard')
def dashboard():
    """User dashboard - requires authentication."""
    return render_template('main/dashboard.html')

