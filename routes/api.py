"""
API Routes

RESTful API endpoints for mobile and third-party integrations.
"""

from datetime import datetime
import os
import uuid
import base64
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from extensions import db
from models.load import Load, LoadStatus
from models.user import User
from models.message import Message

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
    if data is None:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400
    
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
    if data is None:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400
    
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


@api_bp.route('/messages/<int:load_id>', methods=['GET'])
@login_required
def get_messages(load_id):
    """
    Get messages for a specific load.
    
    Accessible to:
    - Assigned shipper or driver (only during active statuses)
    - Admins (any status, all messages)
    """
    load = Load.query.get_or_404(load_id)
    
    # Admins can access all messages regardless of status
    is_admin = current_user.has_admin_access()
    
    if not is_admin:
        # Verify user is shipper or driver
        if current_user.id not in [load.shipper_id, load.driver_id]:
            abort(403)
        
        # Only allow messaging during active statuses for non-admins
        if load.status not in [LoadStatus.NEAR_PICKUP.value, LoadStatus.READY.value, LoadStatus.IN_TRANSIT.value]:
            abort(403)
    
    # Get messages (all for admins, last 50 for regular users)
    if is_admin:
        messages = Message.query.filter_by(load_id=load_id)\
            .order_by(Message.timestamp.asc())\
            .all()
    else:
        messages = Message.query.filter_by(load_id=load_id)\
            .order_by(Message.timestamp.desc())\
            .limit(50)\
            .all()
        # Reverse to show oldest first for non-admins
        messages = list(reversed(messages))
    
    return jsonify([m.to_dict() for m in messages])


@api_bp.route('/messages/<int:load_id>', methods=['POST'])
@login_required
def send_message(load_id):
    """
    Send a message for a specific load.
    
    Only accessible to the assigned shipper or driver.
    Only available when load status is near_pickup, ready, or in_transit.
    Supports text and optional base64-encoded photo.
    """
    load = Load.query.get_or_404(load_id)
    
    # Verify user is shipper or driver
    if current_user.id not in [load.shipper_id, load.driver_id]:
        abort(403)
    
    # Only allow messaging during active statuses
    if load.status not in [LoadStatus.NEAR_PICKUP.value, LoadStatus.READY.value, LoadStatus.IN_TRANSIT.value]:
        abort(403)
    
    # Validate JSON data
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400
    
    content = data.get('content', '').strip() if data.get('content') else None
    photo_b64 = data.get('photo')
    
    # Require at least content or photo
    if not content and not photo_b64:
        return jsonify({'error': 'Message must contain text or photo'}), 400
    
    # Determine receiver (the other party)
    if current_user.id == load.shipper_id:
        receiver_id = load.driver_id
    else:
        receiver_id = load.shipper_id
    
    if receiver_id is None:
        return jsonify({'error': 'Load must have both shipper and driver assigned'}), 400
    
    # Handle photo upload if provided
    photo_url = None
    if photo_b64:
        try:
            # Decode base64 image
            image_data = base64.b64decode(photo_b64)
            
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('static', 'uploads', 'messages')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(upload_dir, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            photo_url = f"/static/uploads/messages/{filename}"
        except Exception as e:
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 400
    
    # Create message
    message = Message(
        load_id=load_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        photo_url=photo_url,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': message.to_dict()
    }), 200

