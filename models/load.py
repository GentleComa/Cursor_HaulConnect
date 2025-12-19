"""
Load Model

Defines the Load model for freight shipments.
"""

from datetime import datetime
from enum import Enum

from extensions import db


class LoadStatus(Enum):
    """Load status enumeration."""
    POSTED = 'posted'
    ACCEPTED = 'accepted'  # Driver has accepted the load
    ASSIGNED = 'assigned'  # Alias for accepted (backward compatibility)
    NEAR_PICKUP = 'near_pickup'  # Driver is near pickup location
    READY = 'ready'  # Load is ready for pickup
    IN_TRANSIT = 'in_transit'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


class Load(db.Model):
    """Load model for freight shipments."""
    
    __tablename__ = 'loads'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Origin
    origin_city = db.Column(db.String(100), nullable=False)
    origin_state = db.Column(db.String(50), nullable=False)
    origin_zip = db.Column(db.String(20))
    origin_address = db.Column(db.String(255))
    origin_lat = db.Column(db.Float, default=0.0)
    origin_lng = db.Column(db.Float, default=0.0)
    
    # Destination
    destination_city = db.Column(db.String(100), nullable=False)
    destination_state = db.Column(db.String(50), nullable=False)
    destination_zip = db.Column(db.String(20))
    destination_address = db.Column(db.String(255))
    dest_lat = db.Column(db.Float, default=0.0)
    dest_lng = db.Column(db.Float, default=0.0)
    
    # Load details
    weight = db.Column(db.Integer)  # in pounds
    distance = db.Column(db.Integer)  # in miles
    equipment_type = db.Column(db.String(50), nullable=False)  # dry_van, flatbed, reefer
    commodity = db.Column(db.String(100))
    special_instructions = db.Column(db.Text)
    
    # Pricing
    rate = db.Column(db.Numeric(10, 2), nullable=False)  # Total rate in dollars
    rate_per_mile = db.Column(db.Numeric(6, 2))
    
    # Dates
    pickup_date = db.Column(db.DateTime, nullable=False)
    delivery_date = db.Column(db.DateTime)
    pickup_window_start = db.Column(db.Time)
    pickup_window_end = db.Column(db.Time)
    
    # Status
    status = db.Column(db.String(20), default=LoadStatus.POSTED.value, index=True)
    
    # Relationships
    shipper_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Tracking
    current_lat = db.Column(db.Float)
    current_lng = db.Column(db.Float)
    last_location_update = db.Column(db.DateTime)
    progress = db.Column(db.Float, default=0.0)  # Progress from 0.0 to 1.0
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Payment relationship
    payment = db.relationship('Payment', backref='load', uselist=False)
    
    def __repr__(self):
        return f'<Load {self.reference_number}>'
    
    @staticmethod
    def generate_reference():
        """Generate a unique reference number."""
        import random
        import string
        prefix = 'HC'
        suffix = ''.join(random.choices(string.digits, k=8))
        return f'{prefix}{suffix}'
    
    @property
    def route_summary(self):
        """Return a short route summary."""
        return f'{self.origin_city}, {self.origin_state} → {self.destination_city}, {self.destination_state}'
    
    def is_active(self):
        """Check if load is still in progress (not delivered or cancelled)."""
        return self.status not in [LoadStatus.DELIVERED.value, LoadStatus.CANCELLED.value]
    
    def assign_driver(self, driver):
        """
        Assign a driver to this load.
        
        Sets status to ASSIGNED for backward compatibility with existing code.
        ACCEPTED and ASSIGNED are treated as equivalent states.
        """
        self.driver_id = driver.id
        self.status = LoadStatus.ASSIGNED.value  # Use ASSIGNED for backward compatibility
        self.assigned_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
    
    def mark_near_pickup(self):
        """Mark load as near pickup location."""
        # Accept both ACCEPTED and ASSIGNED as valid previous states
        if self.status in [LoadStatus.ACCEPTED.value, LoadStatus.ASSIGNED.value]:
            self.status = LoadStatus.NEAR_PICKUP.value
            self.last_updated = datetime.utcnow()
    
    def mark_ready(self):
        """Mark load as ready for pickup."""
        # Accept both ACCEPTED and ASSIGNED as valid previous states
        if self.status in [LoadStatus.ACCEPTED.value, LoadStatus.ASSIGNED.value, LoadStatus.NEAR_PICKUP.value]:
            self.status = LoadStatus.READY.value
            self.last_updated = datetime.utcnow()
    
    def mark_in_transit(self):
        """Mark load as in transit."""
        # Accept both ACCEPTED and ASSIGNED as valid previous states
        if self.status in [LoadStatus.ACCEPTED.value, LoadStatus.ASSIGNED.value, LoadStatus.READY.value]:
            self.status = LoadStatus.IN_TRANSIT.value
            self.last_updated = datetime.utcnow()
    
    def mark_delivered(self):
        """Mark load as delivered."""
        self.status = LoadStatus.DELIVERED.value
        self.delivered_at = datetime.utcnow()
        self.progress = 1.0
        self.last_updated = datetime.utcnow()
    
    def cancel(self):
        """Cancel the load."""
        self.status = LoadStatus.CANCELLED.value
        self.last_updated = datetime.utcnow()
    
    def advance_status(self):
        """
        Advance load status to the next stage in the dispatch flow.
        
        Status flow: accepted/assigned → near_pickup → ready → in_transit → delivered
        """
        next_status_map = {
            LoadStatus.ACCEPTED.value: LoadStatus.NEAR_PICKUP.value,
            LoadStatus.ASSIGNED.value: LoadStatus.NEAR_PICKUP.value,  # Treat ASSIGNED same as ACCEPTED
            LoadStatus.NEAR_PICKUP.value: LoadStatus.READY.value,
            LoadStatus.READY.value: LoadStatus.IN_TRANSIT.value,
            LoadStatus.IN_TRANSIT.value: LoadStatus.DELIVERED.value
        }
        
        if self.status in next_status_map:
            self.status = next_status_map[self.status]
            self.last_updated = datetime.utcnow()
            
            # Update progress based on status
            progress_map = {
                LoadStatus.NEAR_PICKUP.value: 0.2,
                LoadStatus.READY.value: 0.4,
                LoadStatus.IN_TRANSIT.value: 0.7,
                LoadStatus.DELIVERED.value: 1.0
            }
            if self.status in progress_map:
                self.progress = progress_map[self.status]
            
            # Set delivered_at when delivered
            if self.status == LoadStatus.DELIVERED.value:
                self.delivered_at = datetime.utcnow()
            
            return True
        return False

