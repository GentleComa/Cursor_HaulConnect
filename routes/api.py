"""
API Routes

RESTful API endpoints for mobile and third-party integrations.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from extensions import db
from models.load import Load, LoadStatus
from models.user import User

api_bp = Blueprint('api', __name__)


@api_bp.route('/loads')
def get_loads():
    """Get available loads."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Load.query.filter_by(status=LoadStatus.POSTED.value)
    
    # Filters
    origin_state = request.args.get('origin_state')
    dest_state = request.args.get('dest_state')
    equipment = request.args.get('equipment')
    
    if origin_state:
        query = query.filter(Load.origin_state == origin_state)
    if dest_state:
        query = query.filter(Load.destination_state == dest_state)
    if equipment:
        query = query.filter(Load.equipment_type == equipment)
    
    pagination = query.order_by(Load.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    loads = [{
        'id': load.id,
        'reference': load.reference_number,
        'origin': f'{load.origin_city}, {load.origin_state}',
        'destination': f'{load.destination_city}, {load.destination_state}',
        'equipment': load.equipment_type,
        'rate': float(load.rate),
        'pickup_date': load.pickup_date.isoformat() if load.pickup_date else None,
        'weight': load.weight,
        'distance': load.distance
    } for load in pagination.items]
    
    return jsonify({
        'loads': loads,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@api_bp.route('/loads/<int:load_id>')
def get_load(load_id):
    """Get a specific load."""
    load = Load.query.get_or_404(load_id)
    
    return jsonify({
        'id': load.id,
        'reference': load.reference_number,
        'status': load.status,
        'origin': {
            'city': load.origin_city,
            'state': load.origin_state,
            'zip': load.origin_zip
        },
        'destination': {
            'city': load.destination_city,
            'state': load.destination_state,
            'zip': load.destination_zip
        },
        'equipment': load.equipment_type,
        'rate': float(load.rate),
        'weight': load.weight,
        'distance': load.distance,
        'pickup_date': load.pickup_date.isoformat() if load.pickup_date else None,
        'commodity': load.commodity,
        'special_instructions': load.special_instructions
    })


@api_bp.route('/loads/<int:load_id>/tracking', methods=['POST'])
@login_required
def update_tracking(load_id):
    """Update load tracking location."""
    load = Load.query.get_or_404(load_id)
    
    if load.driver_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    
    load.current_lat = data.get('lat')
    load.current_lng = data.get('lng')
    load.last_location_update = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'status': 'success'})


@api_bp.route('/user/profile')
@login_required
def get_profile():
    """Get current user's profile."""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'role': current_user.role,
        'company': current_user.company_name,
        'is_verified': current_user.is_verified
    })


@api_bp.route('/quote', methods=['POST'])
def get_quote():
    """Get a freight quote estimate."""
    data = request.get_json()
    
    origin = data.get('origin')
    destination = data.get('destination')
    equipment = data.get('equipment', 'dry_van')
    weight = data.get('weight', 0)
    
    # Simple rate calculation (would be more complex in production)
    # Base rate + per mile + weight factor
    base_rate = 150
    per_mile_rate = 2.50
    distance = data.get('distance', 500)  # Would calculate from origin/dest
    
    estimated_rate = base_rate + (distance * per_mile_rate)
    
    # Equipment adjustments
    equipment_multipliers = {
        'dry_van': 1.0,
        'flatbed': 1.15,
        'reefer': 1.25,
        'tanker': 1.30
    }
    
    multiplier = equipment_multipliers.get(equipment, 1.0)
    estimated_rate *= multiplier
    
    return jsonify({
        'estimated_rate': round(estimated_rate, 2),
        'rate_per_mile': round(estimated_rate / distance, 2),
        'distance': distance,
        'equipment': equipment
    })

