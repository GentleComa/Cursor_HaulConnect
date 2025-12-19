"""
Loads Routes

Load board, load management, and dispatch operations.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user

from extensions import db
from models.load import Load, LoadStatus
from models.user import User
from utils.decorators import role_required
from utils.freight_quote import calculate_quote

loads_bp = Blueprint('loads', __name__)


@loads_bp.route('/')
def board():
    """Load board - browse available loads."""
    # Filter parameters
    origin_state = request.args.get('origin_state')
    dest_state = request.args.get('dest_state')
    equipment = request.args.get('equipment')
    min_rate = request.args.get('min_rate', type=float)
    
    query = Load.query.filter_by(status=LoadStatus.POSTED.value)
    
    if origin_state:
        query = query.filter(Load.origin_state == origin_state)
    if dest_state:
        query = query.filter(Load.destination_state == dest_state)
    if equipment:
        query = query.filter(Load.equipment_type == equipment)
    if min_rate:
        query = query.filter(Load.rate >= min_rate)
    
    loads = query.order_by(Load.created_at.desc()).all()
    
    return render_template('loads/board.html', loads=loads)


@loads_bp.route('/<int:load_id>')
def detail(load_id):
    """Load detail page."""
    load = Load.query.get_or_404(load_id)
    return render_template('loads/detail.html', load=load)


@loads_bp.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    """Post a new load."""
    if current_user.is_driver():
        flash('Drivers cannot post loads.', 'error')
        return redirect(url_for('loads.board'))
    
    if request.method == 'POST':
        # Extract and validate required fields
        origin_city = request.form.get('origin_city', '').strip()
        origin_state = request.form.get('origin_state', '').strip()
        destination_city = request.form.get('destination_city', '').strip()
        destination_state = request.form.get('destination_state', '').strip()
        equipment_type = request.form.get('equipment_type', '').strip()
        rate_str = request.form.get('rate', '').strip()
        pickup_date_str = request.form.get('pickup_date', '').strip()
        
        # Validate required fields are not empty
        errors = []
        if not origin_city:
            errors.append('Origin city is required.')
        if not origin_state:
            errors.append('Origin state is required.')
        if not destination_city:
            errors.append('Destination city is required.')
        if not destination_state:
            errors.append('Destination state is required.')
        if not equipment_type:
            errors.append('Equipment type is required.')
        if not rate_str:
            errors.append('Rate is required.')
        if not pickup_date_str:
            errors.append('Pickup date is required.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('loads/post.html')
        
        # Parse pickup_date from HTML5 date input (format: "YYYY-MM-DD")
        try:
            pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid pickup date format.', 'error')
            return render_template('loads/post.html')
        
        # Parse rate as float
        try:
            rate = float(rate_str)
            if rate <= 0:
                flash('Rate must be greater than zero.', 'error')
                return render_template('loads/post.html')
        except ValueError:
            flash('Rate must be a valid number.', 'error')
            return render_template('loads/post.html')
        
        # Extract optional fields
        origin_zip = request.form.get('origin_zip', '').strip() or None
        destination_zip = request.form.get('destination_zip', '').strip() or None
        weight_str = request.form.get('weight', '').strip()
        weight = None
        if weight_str:
            try:
                weight = int(weight_str)
                if weight <= 0:
                    flash('Weight must be greater than zero.', 'error')
                    return render_template('loads/post.html')
            except ValueError:
                flash('Weight must be a valid number.', 'error')
                return render_template('loads/post.html')
        
        commodity = request.form.get('commodity', '').strip() or None
        special_instructions = request.form.get('special_instructions', '').strip() or None
        
        load = Load(
            reference_number=Load.generate_reference(),
            shipper_id=current_user.id,
            origin_city=origin_city,
            origin_state=origin_state,
            origin_zip=origin_zip,
            destination_city=destination_city,
            destination_state=destination_state,
            destination_zip=destination_zip,
            equipment_type=equipment_type,
            weight=weight,
            rate=rate,
            pickup_date=pickup_date,
            commodity=commodity,
            special_instructions=special_instructions
        )
        
        db.session.add(load)
        db.session.commit()
        
        flash('Load posted successfully!', 'success')
        return redirect(url_for('loads.detail', load_id=load.id))
    
    return render_template('loads/post.html')


# ============================================================================
# Shipper Routes
# ============================================================================

@loads_bp.route('/shipper/loads')
@login_required
@role_required('shipper', 'broker')
def shipper_list():
    """View all loads posted by current shipper."""
    loads = Load.query.filter_by(shipper_id=current_user.id)\
        .order_by(Load.created_at.desc()).all()
    return render_template('loads/shipper_list.html', loads=loads)


@loads_bp.route('/shipper/quote', methods=['GET'])
@login_required
@role_required('shipper', 'broker')
def quote_form():
    """Show quote form for shippers."""
    return render_template('loads/quote_form.html')


@loads_bp.route('/shipper/quote', methods=['POST'])
@login_required
@role_required('shipper', 'broker')
def quote_calculate():
    """Process quote input and show estimated cost."""
    pickup_zip = request.form.get('pickup_zip', '').strip()
    dropoff_zip = request.form.get('dropoff_zip', '').strip()
    miles_str = request.form.get('miles', '').strip()
    weight_str = request.form.get('weight', '').strip()
    
    # Validate required fields
    errors = []
    if not pickup_zip:
        errors.append('Pickup ZIP code is required.')
    if not dropoff_zip:
        errors.append('Dropoff ZIP code is required.')
    if not miles_str:
        errors.append('Mileage is required.')
    if not weight_str:
        errors.append('Weight is required.')
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template('loads/quote_form.html')
    
    # Validate and parse miles
    try:
        miles = int(miles_str)
        if miles < 40 or miles > 400:
            flash('Mileage must be between 40 and 400 miles.', 'error')
            return render_template('loads/quote_form.html')
    except ValueError:
        flash('Mileage must be a valid number.', 'error')
        return render_template('loads/quote_form.html')
    
    # Validate and parse weight
    try:
        weight = int(weight_str)
        if weight < 500 or weight > 28000:
            flash('Weight must be between 500 and 28,000 lbs.', 'error')
            return render_template('loads/quote_form.html')
    except ValueError:
        flash('Weight must be a valid number.', 'error')
        return render_template('loads/quote_form.html')
    
    # Calculate quote
    try:
        estimated_cost = calculate_quote(miles, weight, pickup_zip, dropoff_zip)
        
        # Store quote in session for pre-filling load form
        session['last_quote'] = {
            'pickup_zip': pickup_zip,
            'dropoff_zip': dropoff_zip,
            'miles': miles,
            'weight': weight,
            'estimated_cost': estimated_cost
        }
        
        return render_template(
            'loads/quote_result.html',
            estimated_cost=estimated_cost,
            miles=miles,
            weight=weight,
            pickup_zip=pickup_zip,
            dropoff_zip=dropoff_zip
        )
    except Exception as e:
        flash(f'Error calculating quote: {str(e)}', 'error')
        return render_template('loads/quote_form.html')


@loads_bp.route('/shipper/loads/new', methods=['GET'])
@login_required
@role_required('shipper', 'broker')
def shipper_form():
    """Form to create a new load."""
    # Pre-fill form with quote data if available
    quote_data = session.get('last_quote', {})
    return render_template('loads/shipper_form.html', quote_data=quote_data)


@loads_bp.route('/shipper/loads', methods=['POST'])
@login_required
@role_required('shipper', 'broker')
def shipper_create():
    """Create a new load (store in DB)."""
    # Extract and validate required fields
    origin_city = request.form.get('origin_city', '').strip()
    origin_state = request.form.get('origin_state', '').strip()
    destination_city = request.form.get('destination_city', '').strip()
    destination_state = request.form.get('destination_state', '').strip()
    equipment_type = request.form.get('equipment_type', '').strip()
    rate_str = request.form.get('rate', '').strip()
    distance_str = request.form.get('distance', '').strip()
    weight_str = request.form.get('weight', '').strip()
    pickup_date_str = request.form.get('pickup_date', '').strip()
    
    # Validate required fields
    errors = []
    if not origin_city:
        errors.append('Origin city is required.')
    if not origin_state:
        errors.append('Origin state is required.')
    if not destination_city:
        errors.append('Destination city is required.')
    if not destination_state:
        errors.append('Destination state is required.')
    if not equipment_type:
        errors.append('Equipment type is required.')
    if not rate_str:
        errors.append('Rate is required.')
    if not distance_str:
        errors.append('Distance is required.')
    if not pickup_date_str:
        errors.append('Pickup date is required.')
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template('loads/shipper_form.html')
    
    # Parse pickup_date
    try:
        pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid pickup date format.', 'error')
        return render_template('loads/shipper_form.html')
    
    # Parse rate and distance
    try:
        rate = float(rate_str)
        if rate <= 0:
            flash('Rate must be greater than zero.', 'error')
            return render_template('loads/shipper_form.html')
    except ValueError:
        flash('Rate must be a valid number.', 'error')
        return render_template('loads/shipper_form.html')
    
    try:
        distance = int(distance_str)
        if distance < 40 or distance > 400:
            flash('Distance must be between 40 and 400 miles.', 'error')
            return render_template('loads/shipper_form.html')
    except ValueError:
        flash('Distance must be a valid number.', 'error')
        return render_template('loads/shipper_form.html')
    
    # Parse optional weight
    weight = None
    if weight_str:
        try:
            weight = int(weight_str)
            if weight < 500 or weight > 28000:
                flash('Weight must be between 500 and 28000 lbs.', 'error')
                return render_template('loads/shipper_form.html')
        except ValueError:
            flash('Weight must be a valid number.', 'error')
            return render_template('loads/shipper_form.html')
    
    # Extract optional fields
    origin_zip = request.form.get('origin_zip', '').strip() or None
    destination_zip = request.form.get('destination_zip', '').strip() or None
    commodity = request.form.get('commodity', '').strip() or None
    special_instructions = request.form.get('special_instructions', '').strip() or None
    
    # Create load (with fake lat/lng for now)
    load = Load(
        reference_number=Load.generate_reference(),
        shipper_id=current_user.id,
        origin_city=origin_city,
        origin_state=origin_state,
        origin_zip=origin_zip,
        destination_city=destination_city,
        destination_state=destination_state,
        destination_zip=destination_zip,
        equipment_type=equipment_type,
        weight=weight,
        distance=distance,
        rate=rate,
        pickup_date=pickup_date,
        commodity=commodity,
        special_instructions=special_instructions,
        origin_lat=0.0,  # TODO: Add geocoding
        origin_lng=0.0,
        dest_lat=0.0,
        dest_lng=0.0
    )
    
    db.session.add(load)
    db.session.commit()
    
    # Clear quote data from session after successful load creation
    if 'last_quote' in session:
        session.pop('last_quote', None)
    
    flash('Load posted successfully!', 'success')
    return redirect(url_for('loads.shipper_detail', load_id=load.id))


@loads_bp.route('/shipper/loads/<int:load_id>')
@login_required
@role_required('shipper', 'broker')
def shipper_detail(load_id):
    """View details for a specific load (shipper view)."""
    load = Load.query.get_or_404(load_id)
    
    # Verify ownership
    if load.shipper_id != current_user.id:
        abort(403)
    
    return render_template('loads/shipper_detail.html', load=load)


# ============================================================================
# Driver Routes
# ============================================================================

@loads_bp.route('/driver/load-board')
@login_required
@role_required('driver')
def driver_board():
    """View all available loads (status == posted)."""
    # Filter parameters
    origin_state = request.args.get('origin_state')
    dest_state = request.args.get('dest_state')
    equipment = request.args.get('equipment')
    min_rate = request.args.get('min_rate', type=float)
    
    query = Load.query.filter_by(status=LoadStatus.POSTED.value)
    
    if origin_state:
        query = query.filter(Load.origin_state == origin_state)
    if dest_state:
        query = query.filter(Load.destination_state == dest_state)
    if equipment:
        query = query.filter(Load.equipment_type == equipment)
    if min_rate:
        query = query.filter(Load.rate >= min_rate)
    
    loads = query.order_by(Load.created_at.desc()).all()
    
    return render_template('loads/driver_board.html', loads=loads)


@loads_bp.route('/driver/loads/<int:load_id>/accept', methods=['POST'])
@login_required
@role_required('driver')
def driver_accept(load_id):
    """Accept a load (update status, assign driver)."""
    load = Load.query.get_or_404(load_id)
    
    if load.status != LoadStatus.POSTED.value:
        flash('This load is no longer available.', 'error')
        return redirect(url_for('loads.driver_board'))
    
    # Check if driver already has an active load
    # Accept both ACCEPTED and ASSIGNED as equivalent states
    active_loads = Load.query.filter_by(
        driver_id=current_user.id
    ).filter(
        Load.status.in_([
            LoadStatus.ACCEPTED.value,
            LoadStatus.ASSIGNED.value,
            LoadStatus.NEAR_PICKUP.value,
            LoadStatus.READY.value,
            LoadStatus.IN_TRANSIT.value
        ])
    ).count()
    
    if active_loads > 0:
        flash('You already have an active load. Please complete it before accepting another.', 'error')
        return redirect(url_for('loads.driver_board'))
    
    load.assign_driver(current_user)
    db.session.commit()
    
    flash('Load accepted successfully!', 'success')
    return redirect(url_for('loads.driver_detail', load_id=load.id))


@loads_bp.route('/driver/loads/<int:load_id>')
@login_required
@role_required('driver')
def driver_detail(load_id):
    """View accepted load (driver view)."""
    load = Load.query.get_or_404(load_id)
    
    # Verify ownership
    if load.driver_id != current_user.id:
        abort(403)
    
    return render_template('loads/driver_detail.html', load=load)


# ============================================================================
# Legacy Routes (for backward compatibility)
# ============================================================================

@loads_bp.route('/<int:load_id>/book', methods=['POST'])
@login_required
def book(load_id):
    """Book a load (driver only) - legacy route."""
    if not current_user.is_driver():
        flash('Only drivers can book loads.', 'error')
        return redirect(url_for('loads.detail', load_id=load_id))
    
    load = Load.query.get_or_404(load_id)
    
    if load.status != LoadStatus.POSTED.value:
        flash('This load is no longer available.', 'error')
        return redirect(url_for('loads.detail', load_id=load_id))
    
    load.assign_driver(current_user)
    db.session.commit()
    
    flash('Load booked successfully!', 'success')
    return redirect(url_for('dashboard.index'))


@loads_bp.route('/<int:load_id>/update-status', methods=['POST'])
@login_required
def update_status(load_id):
    """Update load status with proper transition validation."""
    load = Load.query.get_or_404(load_id)
    
    # Verify ownership
    if load.driver_id != current_user.id and load.shipper_id != current_user.id:
        abort(403)
    
    new_status = request.form.get('status')
    
    # Status transitions with validation
    if new_status == 'near_pickup' and load.driver_id == current_user.id:
        load.mark_near_pickup()
    elif new_status == 'ready' and load.driver_id == current_user.id:
        load.mark_ready()
    elif new_status == 'in_transit' and load.driver_id == current_user.id:
        load.mark_in_transit()
    elif new_status == 'delivered' and load.driver_id == current_user.id:
        load.mark_delivered()
    elif new_status == 'cancelled' and load.shipper_id == current_user.id:
        # Only allow cancellation if load is not in transit or delivered
        if load.status not in [LoadStatus.IN_TRANSIT.value, LoadStatus.DELIVERED.value]:
            load.cancel()
        else:
            flash('Cannot cancel a load that is in transit or already delivered.', 'error')
            return redirect(url_for('loads.detail', load_id=load_id))
    else:
        flash('Invalid status transition or insufficient permissions.', 'error')
        return redirect(url_for('loads.detail', load_id=load_id))
    
    db.session.commit()
    flash('Load status updated.', 'success')
    
    # Redirect based on user role
    if current_user.is_driver():
        return redirect(url_for('loads.driver_detail', load_id=load_id))
    else:
        return redirect(url_for('loads.shipper_detail', load_id=load_id))


@loads_bp.route('/my-loads')
@login_required
def my_loads():
    """View user's loads."""
    if current_user.is_driver():
        loads = Load.query.filter_by(driver_id=current_user.id)\
            .order_by(Load.created_at.desc()).all()
    else:
        loads = Load.query.filter_by(shipper_id=current_user.id)\
            .order_by(Load.created_at.desc()).all()
    
    return render_template('loads/my_loads.html', loads=loads)

