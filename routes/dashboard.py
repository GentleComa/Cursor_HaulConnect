"""
Dashboard Routes

User dashboard and overview pages.
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models.load import Load, LoadStatus
from models.payment import Payment

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page."""
    # Get user-specific stats
    if current_user.is_driver():
        assigned_loads = Load.query.filter_by(
            driver_id=current_user.id,
            status=LoadStatus.ASSIGNED.value
        ).count()
        
        in_transit = Load.query.filter_by(
            driver_id=current_user.id,
            status=LoadStatus.IN_TRANSIT.value
        ).count()
        
        completed = Load.query.filter_by(
            driver_id=current_user.id,
            status=LoadStatus.DELIVERED.value
        ).count()
        
        recent_loads = Load.query.filter_by(driver_id=current_user.id)\
            .order_by(Load.created_at.desc()).limit(5).all()
        
        stats = {
            'assigned': assigned_loads,
            'in_transit': in_transit,
            'completed': completed
        }
    else:
        # Shipper/Broker stats
        posted_loads = Load.query.filter_by(shipper_id=current_user.id).count()
        active_loads = Load.query.filter_by(
            shipper_id=current_user.id
        ).filter(Load.status.in_([LoadStatus.ASSIGNED.value, LoadStatus.IN_TRANSIT.value])).count()
        
        recent_loads = Load.query.filter_by(shipper_id=current_user.id)\
            .order_by(Load.created_at.desc()).limit(5).all()
        
        stats = {
            'posted': posted_loads,
            'active': active_loads
        }
    
    return render_template('dashboard/index.html', stats=stats, recent_loads=recent_loads)


@dashboard_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('dashboard/profile.html')


@dashboard_bp.route('/settings')
@login_required
def settings():
    """User settings page."""
    return render_template('dashboard/settings.html')


@dashboard_bp.route('/payments')
@login_required
def payments():
    """Payment history page."""
    if current_user.is_driver():
        payments = Payment.query.filter_by(driver_id=current_user.id)\
            .order_by(Payment.created_at.desc()).all()
    else:
        # Get payments for loads posted by this user
        payments = Payment.query.join(Load).filter(Load.shipper_id == current_user.id)\
            .order_by(Payment.created_at.desc()).all()
    
    return render_template('dashboard/payments.html', payments=payments)

