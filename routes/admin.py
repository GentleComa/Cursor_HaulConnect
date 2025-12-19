"""
Admin Routes

Administrative functions and management interface.
"""

from functools import wraps
from datetime import datetime
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
        if not current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        if not current_user.has_admin_access():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard overview."""
    from datetime import datetime, timedelta
    
    stats = {
        'total_users': User.query.count(),
        'total_drivers': User.query.filter_by(role='driver').count(),
        'total_shippers': User.query.filter(User.role.in_(['shipper', 'broker'])).count(),
        'total_loads': Load.query.count(),
        'active_loads': Load.query.filter(Load.status.in_([
            LoadStatus.POSTED.value,
            LoadStatus.ASSIGNED.value,
            LoadStatus.NEAR_PICKUP.value,
            LoadStatus.READY.value,
            LoadStatus.IN_TRANSIT.value
        ])).count(),
        'completed_loads': Load.query.filter_by(status=LoadStatus.DELIVERED.value).count(),
        'cancelled_loads': Load.query.filter_by(status=LoadStatus.CANCELLED.value).count(),
        'posted_loads': Load.query.filter_by(status=LoadStatus.POSTED.value).count(),
        'in_transit_loads': Load.query.filter_by(status=LoadStatus.IN_TRANSIT.value).count()
    }
    
    # Payment stats (if Payment model exists)
    try:
        stats['total_payments'] = Payment.query.count()
        stats['completed_payments'] = Payment.query.filter_by(status='completed').count()
        stats['pending_payments'] = Payment.query.filter_by(status='pending').count()
    except:
        stats['total_payments'] = 0
        stats['completed_payments'] = 0
        stats['pending_payments'] = 0
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_loads = Load.query.order_by(Load.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, 
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


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(request.referrer or url_for('admin.users'))


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


@admin_bp.route('/shipments')
@admin_bp.route('/loads')
@login_required
@admin_required
def shipments():
    """Shipment (load) management page."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    
    query = Load.query
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Load.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/shipments.html', loads=pagination.items, pagination=pagination, status=status)


@admin_bp.route('/shipments/<int:load_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_load(load_id):
    """Cancel a load (admin action)."""
    load = Load.query.get_or_404(load_id)
    
    # Only allow cancellation if not already delivered or cancelled
    if load.status in [LoadStatus.DELIVERED.value, LoadStatus.CANCELLED.value]:
        flash('Cannot cancel a load that is already delivered or cancelled.', 'error')
        return redirect(request.referrer or url_for('admin.shipments'))
    
    load.status = LoadStatus.CANCELLED.value
    load.last_updated = datetime.utcnow()
    db.session.commit()
    
    flash(f'Load {load.reference_number} has been cancelled.', 'success')
    return redirect(url_for('admin.shipments'))


@admin_bp.route('/idle-alerts')
@login_required
@admin_required
def idle_alerts():
    """
    View idle alerts (idle_30 status loads).
    
    Note: This requires idle monitoring fields on the Load model.
    If idle monitoring is not implemented, this will show an empty list.
    """
    # Query loads with idle_30 status (if idle_status field exists)
    # For now, return empty list as idle monitoring fields may not be present
    try:
        # Try to query by idle_status if the field exists
        idle_loads = Load.query.filter(
            Load.status == LoadStatus.IN_TRANSIT.value
        ).all()
        
        # Filter for idle_30 if idle_status field exists
        # This is a placeholder - actual implementation requires idle_status field
        alerts = []
        for load in idle_loads:
            # Check if load has idle_status attribute (may not exist)
            if hasattr(load, 'idle_status') and getattr(load, 'idle_status', None) == 'idle_30':
                alerts.append(load)
    except:
        alerts = []
    
    return render_template('admin/idle_alerts.html', alerts=alerts)


@admin_bp.route('/idle-alerts/<int:load_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_idle_alert(load_id):
    """
    Resolve an idle alert (admin action).
    
    Note: This requires idle monitoring fields on the Load model.
    """
    load = Load.query.get_or_404(load_id)
    
    # Check if idle monitoring is implemented
    if not hasattr(load, 'idle_status'):
        flash('Idle monitoring is not currently implemented.', 'error')
        return redirect(url_for('admin.idle_alerts'))
    
    # Resolve idle status
    if load.idle_status == 'idle_30':
        load.idle_status = 'active'
        
        # Log resolution in idle_log if it exists
        if hasattr(load, 'idle_log'):
            import json
            from datetime import datetime
            log = json.loads(load.idle_log) if load.idle_log else []
            log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active",
                "resolved_by": "admin",
                "notes": f"Resolved by admin: {current_user.email}"
            })
            load.idle_log = json.dumps(log)
        
        db.session.commit()
        flash(f'Idle alert for load {load.reference_number} has been resolved.', 'success')
    else:
        flash('This load is not in idle_30 status.', 'error')
    
    return redirect(url_for('admin.idle_alerts'))


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

