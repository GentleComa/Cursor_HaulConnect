"""
Admin Routes

Administrative functions and management interface.
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from models.user import User
from models.load import Load, LoadStatus
from models.payment import Payment

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard."""
    stats = {
        'total_users': User.query.count(),
        'total_drivers': User.query.filter_by(role='driver').count(),
        'total_shippers': User.query.filter(User.role.in_(['shipper', 'broker'])).count(),
        'total_loads': Load.query.count(),
        'active_loads': Load.query.filter(Load.status.in_([
            LoadStatus.POSTED.value,
            LoadStatus.ASSIGNED.value,
            LoadStatus.IN_TRANSIT.value
        ])).count(),
        'completed_loads': Load.query.filter_by(status=LoadStatus.DELIVERED.value).count()
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_loads = Load.query.order_by(Load.created_at.desc()).limit(10).all()
    
    return render_template('admin/index.html', stats=stats, 
                          recent_users=recent_users, recent_loads=recent_loads)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page."""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role')
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=pagination.items, pagination=pagination)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """User detail page."""
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_user(user_id):
    """Verify a user."""
    user = User.query.get_or_404(user_id)
    user.is_verified = True
    db.session.commit()
    
    flash(f'User {user.username} has been verified.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/loads')
@login_required
@admin_required
def loads():
    """Load management page."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    
    query = Load.query
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Load.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/loads.html', loads=pagination.items, pagination=pagination)


@admin_bp.route('/payments')
@login_required
@admin_required
def payments():
    """Payment management page."""
    page = request.args.get('page', 1, type=int)
    
    pagination = Payment.query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/payments.html', payments=pagination.items, pagination=pagination)

