"""
Authentication Routes

Handles user authentication: login, logout, registration, password reset.

Passwordless authentication is supported ONLY for development/testing.
Controlled via AUTH_PASSWORD_REQUIRED config flag.
"""

from datetime import datetime
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from extensions import db
from models.user import User

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    """
    Validate that a redirect URL is safe (internal to the application).
    
    Prevents open redirect attacks by ensuring redirects only go to:
    - Relative URLs (starting with /)
    - Absolute URLs with the same host as the current request
    
    Args:
        target: The URL to validate
        
    Returns:
        True if the URL is safe to redirect to, False otherwise
    """
    if not target:
        return False
    
    # Parse the target URL
    parsed_target = urlparse(target)
    
    # Allow relative URLs (no netloc, starts with /)
    if not parsed_target.netloc:
        return target.startswith('/')
    
    # For absolute URLs, check if netloc matches current request host
    ref_url = urlparse(request.host_url)
    return parsed_target.netloc == ref_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    password_required = current_app.config.get('AUTH_PASSWORD_REQUIRED', True)
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Passwordless mode: login by email only
        if not password_required:
            user = User.query.filter_by(email=email).first()
            if user and user.is_active:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                # Validate redirect URL to prevent open redirect attacks
                if next_page and is_safe_url(next_page):
                    flash('Welcome back! (Passwordless mode)', 'success')
                    return redirect(next_page)
                else:
                    flash('Welcome back! (Passwordless mode)', 'success')
                    return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid email or account is inactive.', 'error')
        else:
            # Normal password-based authentication
            user = User.query.filter_by(email=email).first()
            
            if user and user.is_active and user.check_password(password):
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                # Validate redirect URL to prevent open redirect attacks
                if next_page and is_safe_url(next_page):
                    flash('Welcome back!', 'success')
                    return redirect(next_page)
                else:
                    flash('Welcome back!', 'success')
                    return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', password_required=password_required)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    # Use root index endpoint registered in routes/__init__.py
    return redirect(url_for('index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    password_required = current_app.config.get('AUTH_PASSWORD_REQUIRED', True)
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role', 'driver')
        
        # Safety Rule: Prevent admin creation through registration
        # Admin accounts must be created manually in the database
        if role == 'admin':
            flash('Admin accounts cannot be created through registration. Contact system administrator.', 'error')
            return render_template('auth/register.html', password_required=password_required)
        
        # Validation
        if password_required:
            if not password:
                flash('Password is required.', 'error')
                return render_template('auth/register.html', password_required=password_required)
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('auth/register.html', password_required=password_required)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register.html', password_required=password_required)
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('auth/register.html', password_required=password_required)
        
        # Create user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        
        # Set password based on configuration
        if password_required:
            user.set_password(password)
        else:
            user.set_password(None)
        
        db.session.add(user)
        db.session.commit()
        
        if password_required:
            flash('Account created successfully! Please log in.', 'success')
        else:
            flash('Account created successfully! You can now log in without a password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', password_required=password_required)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request page."""
    # TODO: Implement password reset
    return render_template('auth/forgot_password.html')

