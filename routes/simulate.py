"""
Simulation Routes

Development/testing routes for simulating freight operations.
Only available in development mode.
"""

from flask import Blueprint, jsonify, request, current_app, abort, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import random

from extensions import db
from models.user import User
from models.load import Load, LoadStatus
from models.payment import Payment, PaymentStatus
from utils.decorators import role_required
from utils.bulk_simulator import create_bulk_shipments

# Import admin_required from admin routes
def admin_required(f):
    """Decorator to require admin access."""
    from functools import wraps
    from flask import abort
    from flask_login import current_user
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        if not current_user.has_admin_access():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

simulate_bp = Blueprint('simulate', __name__)


def dev_only(f):
    """Decorator to only allow in development mode."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get('DEBUG', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@simulate_bp.before_request
def restrict_to_debug():
    """Restrict all simulate routes to DEBUG mode only."""
    if not current_app.config.get('DEBUG', False):
        abort(403)


@simulate_bp.route('/create-test-users', methods=['POST'])
@dev_only
def create_test_users():
    """
    Create test users for development.
    
    Note: Uses hardcoded password 'password123' for convenience in dev/testing.
    This route is protected by @dev_only decorator and only works when DEBUG=True.
    """
    users_created = []
    
    # Create test driver
    driver = User.query.filter_by(email='driver@test.com').first()
    if not driver:
        driver = User(
            email='driver@test.com',
            username='testdriver',
            first_name='Test',
            last_name='Driver',
            role='driver',
            mc_number='MC123456',
            equipment_type='dry_van',
            is_verified=True
        )
        # Hardcoded test password - acceptable for dev-only route
        driver.set_password('password123')
        db.session.add(driver)
        users_created.append('driver@test.com')
    
    # Create test shipper
    shipper = User.query.filter_by(email='shipper@test.com').first()
    if not shipper:
        shipper = User(
            email='shipper@test.com',
            username='testshipper',
            first_name='Test',
            last_name='Shipper',
            role='shipper',
            company_name='Test Shipping Co',
            is_verified=True
        )
        shipper.set_password('password123')
        db.session.add(shipper)
        users_created.append('shipper@test.com')
    
    # Create test admin
    admin = User.query.filter_by(email='admin@test.com').first()
    if not admin:
        admin = User(
            email='admin@test.com',
            username='testadmin',
            first_name='Test',
            last_name='Admin',
            role='admin',
            is_verified=True
        )
        admin.set_password('password123')
        db.session.add(admin)
        users_created.append('admin@test.com')
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'users_created': users_created,
        'message': 'All test users use password: password123'
    })


@simulate_bp.route('/create-test-loads', methods=['POST'])
@dev_only
def create_test_loads():
    """Create test loads for development."""
    shipper = User.query.filter_by(email='shipper@test.com').first()
    
    if not shipper:
        return jsonify({'error': 'Create test users first'}), 400
    
    cities = [
        ('Chicago', 'IL'),
        ('Los Angeles', 'CA'),
        ('Dallas', 'TX'),
        ('Atlanta', 'GA'),
        ('Phoenix', 'AZ'),
        ('Denver', 'CO'),
        ('Seattle', 'WA'),
        ('Miami', 'FL'),
        ('New York', 'NY'),
        ('Boston', 'MA')
    ]
    
    equipment_types = ['dry_van', 'flatbed', 'reefer']
    commodities = ['Electronics', 'Furniture', 'Food Products', 'Machinery', 'Auto Parts']
    
    loads_created = 0
    
    for i in range(10):
        origin = random.choice(cities)
        dest = random.choice([c for c in cities if c != origin])
        
        load = Load(
            reference_number=Load.generate_reference(),
            shipper_id=shipper.id,
            origin_city=origin[0],
            origin_state=origin[1],
            origin_zip=f'{random.randint(10000, 99999)}',
            destination_city=dest[0],
            destination_state=dest[1],
            destination_zip=f'{random.randint(10000, 99999)}',
            equipment_type=random.choice(equipment_types),
            weight=random.randint(10000, 45000),
            distance=random.randint(200, 2000),
            rate=random.randint(800, 5000),
            pickup_date=datetime.utcnow() + timedelta(days=random.randint(1, 14)),
            commodity=random.choice(commodities),
            status=LoadStatus.POSTED.value
        )
        
        db.session.add(load)
        loads_created += 1
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'loads_created': loads_created
    })


@simulate_bp.route('/simulate-delivery/<int:load_id>', methods=['POST'])
@dev_only
def simulate_delivery(load_id):
    """Simulate a load delivery lifecycle."""
    load = Load.query.get_or_404(load_id)
    
    driver = User.query.filter_by(email='driver@test.com').first()
    if not driver:
        return jsonify({'error': 'Create test users first'}), 400
    
    # Assign driver
    if load.status == LoadStatus.POSTED.value:
        load.assign_driver(driver)
        db.session.commit()
        return jsonify({'status': 'assigned', 'load_id': load.id})
    
    # Mark in transit
    if load.status == LoadStatus.ASSIGNED.value:
        load.mark_in_transit()
        db.session.commit()
        return jsonify({'status': 'in_transit', 'load_id': load.id})
    
    # Mark delivered and create payment
    if load.status == LoadStatus.IN_TRANSIT.value:
        load.mark_delivered()
        
        # Create payment
        payment = Payment(
            transaction_id=Payment.generate_transaction_id(),
            load_id=load.id,
            driver_id=driver.id,
            amount=load.rate,
            platform_fee=float(load.rate) * 0.05,  # 5% platform fee
            driver_payout=float(load.rate) * 0.95,
            status=PaymentStatus.COMPLETED.value,
            payment_method='bank_transfer'
        )
        payment.mark_completed()
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'status': 'delivered',
            'load_id': load.id,
            'payment_id': payment.id
        })
    
    return jsonify({'status': load.status, 'message': 'No action taken'})


@simulate_bp.route('/reset-database', methods=['POST'])
@dev_only
def reset_database():
    """Reset the database (dangerous - dev only)."""
    confirm = request.json.get('confirm')
    
    if confirm != 'RESET':
        return jsonify({'error': 'Must confirm with {"confirm": "RESET"}'}), 400
    
    # Delete all data
    Payment.query.delete()
    Load.query.delete()
    User.query.delete()
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Database reset complete'})


@simulate_bp.route('/dev-dashboard')
@login_required
@role_required('driver')
@dev_only
def dev_dashboard():
    """
    Developer dashboard for simulating load dispatch flow.
    
    Only available in DEBUG mode and only for drivers.
    Shows all loads assigned to the current driver.
    """
    # Get all loads assigned to current driver that are not delivered or cancelled
    assigned_loads = Load.query.filter_by(
        driver_id=current_user.id
    ).filter(
        Load.status.notin_([LoadStatus.DELIVERED.value, LoadStatus.CANCELLED.value])
    ).order_by(Load.created_at.desc()).all()
    
    return render_template('simulate/dev_dashboard.html', loads=assigned_loads)


@simulate_bp.route('/create-bulk/<int:count>', methods=['POST'])
@login_required
@admin_required
@dev_only
def create_bulk_shipments_route(count):
    """
    Create bulk simulated shipments.
    
    Only accessible by admins in DEBUG mode.
    """
    if count < 1 or count > 50:
        return jsonify({'error': 'Count must be between 1 and 50'}), 400
    
    try:
        from utils.bulk_simulator import SIMULATION_LOGS, generate_simulation_report
        
        shipments, run_id = create_bulk_shipments(count)
        
        # Generate report
        report = generate_simulation_report(run_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Created {len(shipments)} simulated shipments',
            'run_id': run_id,
            'shipments': shipments,
            'report': report
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': f'Error creating shipments: {str(e)}',
            'traceback': traceback.format_exc() if current_app.config.get('DEBUG') else None
        }), 500


@simulate_bp.route('/map-view')
@login_required
@admin_required
@dev_only
def map_view():
    """
    Map view showing all simulated shipments.
    
    Only accessible by admins in DEBUG mode.
    """
    # Get all active loads (not delivered or cancelled)
    active_loads = Load.query.filter(
        Load.status.notin_([LoadStatus.DELIVERED.value, LoadStatus.CANCELLED.value])
    ).all()
    
    # Format loads for map display
    map_loads = []
    for load in active_loads:
        map_loads.append({
            'id': load.id,
            'reference_number': load.reference_number,
            'driver_id': load.driver_id,
            'driver_name': load.driver.full_name if load.driver else 'Unassigned',
            'status': load.status,
            'origin_lat': load.origin_lat,
            'origin_lng': load.origin_lng,
            'dest_lat': load.dest_lat,
            'dest_lng': load.dest_lng,
            'current_lat': load.current_lat,
            'current_lng': load.current_lng,
            'idle_status': getattr(load, 'idle_status', None),
            'progress': load.progress or 0.0
        })
    
    return render_template('simulate/map_view.html', loads=map_loads)


@simulate_bp.route('/api/map-data')
@login_required
@admin_required
@dev_only
def map_data():
    """
    API endpoint to get current map data (for polling).
    """
    active_loads = Load.query.filter(
        Load.status.notin_([LoadStatus.DELIVERED.value, LoadStatus.CANCELLED.value])
    ).all()
    
    map_loads = []
    for load in active_loads:
        map_loads.append({
            'id': load.id,
            'reference_number': load.reference_number,
            'driver_id': load.driver_id,
            'driver_name': load.driver.full_name if load.driver else 'Unassigned',
            'status': load.status,
            'origin_lat': load.origin_lat,
            'origin_lng': load.origin_lng,
            'dest_lat': load.dest_lat,
            'dest_lng': load.dest_lng,
            'current_lat': load.current_lat,
            'current_lng': load.current_lng,
            'idle_status': getattr(load, 'idle_status', None),
            'progress': load.progress or 0.0
        })
    
    return jsonify({'loads': map_loads})


@simulate_bp.route('/report/latest')
@simulate_bp.route('/report/<run_id>')
@login_required
@admin_required
@dev_only
def view_simulation_report(run_id=None):
    """
    View simulation report (HTML).
    
    Shows latest report if run_id is not provided.
    """
    from utils.bulk_simulator import generate_simulation_report, SIMULATION_LOGS
    
    report = generate_simulation_report(run_id)
    
    if "error" in report:
        flash(report["error"], "error")
        return redirect(url_for('simulate.dev_dashboard'))
    
    return render_template('simulate/report.html', report=report)


@simulate_bp.route('/report/<run_id>/download')
@login_required
@admin_required
@dev_only
def download_simulation_report(run_id):
    """
    Download simulation report as JSON.
    """
    from flask import Response
    from utils.bulk_simulator import generate_simulation_report
    import json
    
    report = generate_simulation_report(run_id)
    
    if "error" in report:
        return jsonify({"error": report["error"]}), 404
    
    json_str = json.dumps(report, indent=2)
    
    return Response(
        json_str,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=simulation_report_{run_id}.json'
        }
    )


@simulate_bp.route('/advance/<int:load_id>', methods=['POST'])
@login_required
@role_required('driver')
@dev_only
def advance_status(load_id):
    """
    Advance a load's status to the next stage.
    
    Only available in DEBUG mode and only for the assigned driver.
    """
    load = Load.query.get_or_404(load_id)
    
    # Verify load is assigned to current driver
    if load.driver_id != current_user.id:
        flash('You can only advance loads assigned to you.', 'error')
        return redirect(url_for('simulate.dev_dashboard'))
    
    # Check if load can be advanced
    if load.status == LoadStatus.DELIVERED.value:
        flash('Load is already delivered.', 'info')
        return redirect(url_for('simulate.dev_dashboard'))
    
    # Advance status
    if load.advance_status():
        db.session.commit()
        flash(f'Load status advanced to {load.status.replace("_", " ").title()}.', 'success')
    else:
        flash('Cannot advance load from current status.', 'error')
    
    return redirect(url_for('simulate.dev_dashboard'))

