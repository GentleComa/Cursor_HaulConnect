"""
Bulk Shipment Simulator

Creates and simulates multiple test shipments with full lifecycle,
messaging, idle alerts, and status progression.
"""

import random
import json
import time
import math
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from flask import current_app
from extensions import db
from models.user import User
from models.load import Load, LoadStatus
from models.message import Message
from models.payment import Payment, PaymentStatus
from utils.freight_quote import calculate_quote


# Global simulation logs storage (thread-safe with lock)
SIMULATION_LOGS = {}
SIMULATION_LOGS_LOCK = threading.Lock()
SIMULATION_RUN_ID = None


class SimulationLogEntry:
    """Log entry for a single shipment simulation."""
    
    def __init__(self, shipment_id: int, driver_id: int, shipper_id: int, run_id: str = None):
        self.shipment_id = shipment_id
        self.driver_id = driver_id
        self.shipper_id = shipper_id
        self.run_id = run_id or SIMULATION_RUN_ID
        self.events = []
        self.errors = []
        self.idle_status = None
        self.idle_events = []
        self.success = False
        self.delivery_photo = False
        self.message_count = 0
        self.system_messages = 0
        self.driver_messages = 0
        self.shipper_messages = 0
        self.admin_messages = 0
        self.start_time = datetime.utcnow()
        self.end_time = None
        self.origin_zip = None
        self.destination_zip = None
        self.status_transitions = []
    
    def log_event(self, event_type: str, message: str, metadata: Dict = None):
        """Log a simulation event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,  # SYSTEM, DRIVER, SHIPPER, GPS, ADMIN, MESSAGE, STATUS
            "message": message
        }
        if metadata:
            event["metadata"] = metadata
        self.events.append(event)
    
    def log_error(self, message: str, error_type: str = "ERROR"):
        """Log an error or fault."""
        error = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,  # ERROR, TIMEOUT, MISSING_FIELD, INVALID_TRANSITION
            "message": message
        }
        self.errors.append(error)
    
    def log_status_transition(self, from_status: str, to_status: str):
        """Log a status transition."""
        self.status_transitions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "from": from_status,
            "to": to_status
        })
        self.log_event("STATUS", f"Status changed: {from_status} → {to_status}")
    
    def log_message(self, sender_type: str, content: str):
        """Log a message event."""
        self.message_count += 1
        if sender_type == "system":
            self.system_messages += 1
        elif sender_type == "driver":
            self.driver_messages += 1
        elif sender_type == "shipper":
            self.shipper_messages += 1
        elif sender_type == "admin":
            self.admin_messages += 1
        
        self.log_event("MESSAGE", f"{sender_type.title()} message: {content[:50]}...")
    
    def finish(self, success: bool = True):
        """Mark simulation as complete."""
        self.end_time = datetime.utcnow()
        self.success = success
        self.log_event("SYSTEM", f"Simulation {'completed successfully' if success else 'failed'}")
    
    def to_dict(self) -> Dict:
        """Convert log entry to dictionary for JSON serialization."""
        elapsed = None
        if self.end_time and self.start_time:
            elapsed = (self.end_time - self.start_time).total_seconds()
        
        return {
            "shipment_id": self.shipment_id,
            "driver_id": self.driver_id,
            "shipper_id": self.shipper_id,
            "run_id": self.run_id,
            "origin_zip": self.origin_zip,
            "destination_zip": self.destination_zip,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": elapsed,
            "success": self.success,
            "delivery_photo": self.delivery_photo,
            "idle_status": self.idle_status,
            "idle_events": self.idle_events,
            "status_transitions": self.status_transitions,
            "message_summary": {
                "total": self.message_count,
                "system": self.system_messages,
                "driver": self.driver_messages,
                "shipper": self.shipper_messages,
                "admin": self.admin_messages
            },
            "events": self.events,
            "errors": self.errors
        }
    
    def validate(self) -> Dict:
        """Validate log entry and return health score."""
        issues = []
        score = 100
        
        # Check for required transitions
        required_statuses = ["posted", "assigned", "near_pickup", "ready", "in_transit", "delivered"]
        actual_statuses = [t["to"] for t in self.status_transitions]
        
        for status in required_statuses:
            if status not in actual_statuses:
                issues.append(f"Missing status transition: {status}")
                score -= 10
        
        # Check for errors
        if self.errors:
            score -= len(self.errors) * 5
            issues.append(f"{len(self.errors)} error(s) occurred")
        
        # Check for delivery photo
        if not self.delivery_photo:
            issues.append("Delivery photo not submitted")
            score -= 5
        
        # Check for messages
        if self.message_count < 3:
            issues.append("Insufficient messaging activity")
            score -= 5
        
        # Check for idle_30 escalation
        if "idle_30" in self.idle_events:
            if self.admin_messages == 0:
                issues.append("idle_30 event but no admin intervention")
                score -= 15
        
        return {
            "health_score": max(0, score),
            "issues": issues,
            "is_healthy": score >= 80
        }


# Texas ZIP codes with approximate lat/lng coordinates
TEXAS_ZIPS = [
    {"zip": "73301", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
    {"zip": "75001", "city": "Addison", "lat": 32.9618, "lng": -96.8292},
    {"zip": "75006", "city": "Carrollton", "lat": 32.9537, "lng": -96.8903},
    {"zip": "75019", "city": "Coppell", "lat": 32.9546, "lng": -96.9900},
    {"zip": "75201", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "77001", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "78201", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78701", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
    {"zip": "79901", "city": "El Paso", "lat": 31.7619, "lng": -106.4850},
    {"zip": "76101", "city": "Fort Worth", "lat": 32.7555, "lng": -97.3308},
    {"zip": "76010", "city": "Arlington", "lat": 32.7357, "lng": -97.1081},
    {"zip": "76541", "city": "Georgetown", "lat": 30.6333, "lng": -97.6772},
    {"zip": "75023", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75024", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75025", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75034", "city": "Frisco", "lat": 33.1507, "lng": -96.8236},
    {"zip": "75035", "city": "Frisco", "lat": 33.1507, "lng": -96.8236},
    {"zip": "75080", "city": "Richardson", "lat": 32.9483, "lng": -96.7299},
    {"zip": "75081", "city": "Richardson", "lat": 32.9483, "lng": -96.7299},
    {"zip": "75082", "city": "Richardson", "lat": 32.9483, "lng": -96.7299},
    {"zip": "75083", "city": "Richardson", "lat": 32.9483, "lng": -96.7299},
    {"zip": "75093", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75094", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75098", "city": "Plano", "lat": 33.0198, "lng": -96.6989},
    {"zip": "75150", "city": "Mesquite", "lat": 32.7668, "lng": -96.5992},
    {"zip": "75154", "city": "Mesquite", "lat": 32.7668, "lng": -96.5992},
    {"zip": "75202", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75203", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75204", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75205", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75206", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75207", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75208", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75209", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "75210", "city": "Dallas", "lat": 32.7767, "lng": -96.7970},
    {"zip": "77002", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77003", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77004", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77005", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77006", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77007", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77008", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77009", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "77010", "city": "Houston", "lat": 29.7604, "lng": -95.3698},
    {"zip": "78202", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78203", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78204", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78205", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78206", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78207", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78208", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78209", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78210", "city": "San Antonio", "lat": 29.4241, "lng": -98.4936},
    {"zip": "78702", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
    {"zip": "78703", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
    {"zip": "78704", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
    {"zip": "78705", "city": "Austin", "lat": 30.2672, "lng": -97.7431},
]


def get_random_texas_zip() -> Dict:
    """Get a random Texas ZIP code with coordinates."""
    return random.choice(TEXAS_ZIPS)


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance in miles between two lat/lng coordinates using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lng1: Longitude of first point
        lat2: Latitude of second point
        lng2: Longitude of second point
    
    Returns:
        Distance in miles
    """
    # Earth's radius in miles
    R = 3959.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance


def calculate_duration_from_distance(miles: float) -> float:
    """
    Calculate base duration in seconds based on distance using tiered mapping.
    
    Args:
        miles: Distance in miles
    
    Returns:
        Base duration in seconds
    """
    if miles < 100:
        return random.uniform(30, 45)  # Short: 30-45s
    elif miles < 200:
        return random.uniform(45, 60)  # Medium: 45-60s
    else:
        return random.uniform(60, 90)  # Long: 60-90s


def get_driver_start_location(pickup_lat: float, pickup_lng: float) -> Tuple[float, float]:
    """
    Calculate driver starting location 25-50 miles from pickup.
    
    Approximately 0.3-0.6 degrees offset (roughly 25-50 miles).
    """
    # Random direction
    direction = random.uniform(0, 2 * 3.14159)  # Random angle in radians
    distance = random.uniform(0.3, 0.6)  # Degrees (roughly 25-50 miles)
    
    start_lat = pickup_lat + (distance * random.choice([-1, 1]) * 0.5)
    start_lng = pickup_lng + (distance * random.choice([-1, 1]) * 0.5)
    
    return start_lat, start_lng


def update_progress_gradually(load: Load, target_progress: float, duration: float, 
                              update_interval: float = 2.0, db_session=None) -> None:
    """
    Gradually update progress from current to target value with intermediate states.
    
    Args:
        load: Load object to update
        target_progress: Target progress value (0.0 to 1.0)
        duration: Total time in seconds to reach target
        update_interval: Seconds between progress updates (default 2.0)
        db_session: Database session (defaults to db.session)
    """
    if db_session is None:
        db_session = db.session
    
    current_progress = load.progress or 0.0
    if current_progress >= target_progress:
        return
    
    progress_diff = target_progress - current_progress
    num_updates = max(1, int(duration / update_interval))
    progress_increment = progress_diff / num_updates
    
    for i in range(num_updates):
        current_progress += progress_increment
        if current_progress > target_progress:
            current_progress = target_progress
        
        load.progress = current_progress
        load.last_updated = datetime.utcnow()
        db_session.commit()
        
        if i < num_updates - 1:  # Don't sleep after last update
            time.sleep(update_interval)


def interpolate_location(lat1: float, lng1: float, lat2: float, lng2: float, 
                         progress: float) -> Tuple[float, float]:
    """
    Interpolate between two GPS coordinates based on progress (0.0 to 1.0).
    
    Args:
        lat1: Starting latitude
        lng1: Starting longitude
        lat2: Ending latitude
        lng2: Ending longitude
        progress: Progress value (0.0 = start, 1.0 = end)
    
    Returns:
        Tuple of (interpolated_lat, interpolated_lng)
    """
    progress = max(0.0, min(1.0, progress))  # Clamp to 0.0-1.0
    lat = lat1 + (lat2 - lat1) * progress
    lng = lng1 + (lng2 - lng1) * progress
    return lat, lng


def create_simulated_shipment(shipper: User, driver: User, shipment_id: int, run_id: str = None, delay_seconds: Optional[float] = None, load: Optional[Load] = None, pickup_zip_data: Optional[Dict] = None, dropoff_zip_data: Optional[Dict] = None) -> Dict:
    """
    Create a single simulated shipment with full lifecycle.
    
    Args:
        shipper: Shipper user
        driver: Driver user
        shipment_id: Unique shipment ID
        run_id: Simulation run ID
        delay_seconds: Total time in seconds to spread the simulation over (if None, calculated from distance)
        load: Pre-created Load object (if None, will be created)
        pickup_zip_data: Pre-selected pickup location data (if None, will be selected)
        dropoff_zip_data: Pre-selected dropoff location data (if None, will be selected)
    
    Returns:
        Dict with shipment details including load_id and simulation results
    """
    # Initialize log entry
    log = SimulationLogEntry(shipment_id, driver.id, shipper.id, run_id)
    log.log_event("SYSTEM", "Starting shipment simulation")
    
    # Track idle delays
    idle_delay_seconds = 0.0
    
    try:
        # Step 1: Select pickup and dropoff locations (if not provided)
        if not pickup_zip_data:
            pickup_zip_data = get_random_texas_zip()
        if not dropoff_zip_data:
            dropoff_zip_data = get_random_texas_zip()
            # Ensure different locations
            while dropoff_zip_data["zip"] == pickup_zip_data["zip"]:
                dropoff_zip_data = get_random_texas_zip()
        
        pickup_zip = pickup_zip_data["zip"]
        dropoff_zip = dropoff_zip_data["zip"]
        
        log.origin_zip = pickup_zip
        log.destination_zip = dropoff_zip
        log.log_event("SYSTEM", f"Selected route: {pickup_zip} → {dropoff_zip}")
        
        # Step 2: Calculate actual distance using Haversine formula
        miles = haversine_distance(
            pickup_zip_data["lat"],
            pickup_zip_data["lng"],
            dropoff_zip_data["lat"],
            dropoff_zip_data["lng"]
        )
        miles = round(miles, 1)  # Round to 1 decimal place
        
        # Calculate base duration from distance
        base_duration = calculate_duration_from_distance(miles)
        
        # Use provided load or create new one
        if load is None:
            weight = random.randint(500, 28000)
            estimated_rate = calculate_quote(int(miles), weight, pickup_zip, dropoff_zip)
            
            # Create the load
            load = Load(
                reference_number=Load.generate_reference(),
                shipper_id=shipper.id,
                origin_zip=pickup_zip,
                origin_city=pickup_zip_data["city"],
                origin_state="TX",
                origin_lat=pickup_zip_data["lat"],
                origin_lng=pickup_zip_data["lng"],
                destination_zip=dropoff_zip,
                destination_city=dropoff_zip_data["city"],
                destination_state="TX",
                dest_lat=dropoff_zip_data["lat"],
                dest_lng=dropoff_zip_data["lng"],
                distance=int(miles),
                weight=weight,
                rate=estimated_rate,
                equipment_type=random.choice(["dry_van", "flatbed", "reefer", "box_truck"]),
                status=LoadStatus.POSTED.value,
                pickup_date=datetime.utcnow() + timedelta(hours=random.randint(1, 24)),
                created_at=datetime.utcnow()
            )
            db.session.add(load)
            db.session.flush()  # Get load.id
        else:
            # Use existing load's distance and rate
            miles = float(load.distance)
            estimated_rate = float(load.rate)
        
        # Store log in global dict (thread-safe)
        with SIMULATION_LOGS_LOCK:
            SIMULATION_LOGS[load.id] = log
        
        log.log_event("SYSTEM", f"Processing load {load.reference_number} (distance: {miles:.1f} miles)")
        log.log_status_transition("none", LoadStatus.POSTED.value)
        
        # Determine idle scenario early to calculate total duration
        idle_scenario = random.choices(
            ["none", "idle_15", "idle_30"],
            weights=[75, 20, 5]
        )[0]
        
        # Calculate idle delays
        if idle_scenario == "idle_15":
            idle_delay_seconds = 30.0
        elif idle_scenario == "idle_30":
            idle_delay_seconds = 45.0
        else:
            idle_delay_seconds = 0.0
        
        # Calculate total duration (base + idle delays, or use provided delay_seconds)
        if delay_seconds is None:
            total_duration = base_duration + idle_delay_seconds
        else:
            total_duration = delay_seconds
        
        # Calculate delay between status transitions (spread over total_duration)
        # We have ~6 major transitions: posted->assigned->near_pickup->ready->in_transit->delivered
        transition_delay = total_duration / 6.0
        
        log.log_event("SYSTEM", f"Base duration: {base_duration:.1f}s, Idle delay: {idle_delay_seconds:.1f}s, Total: {total_duration:.1f}s")
        
        # Step 3: Assign driver (if not already assigned)
        if load.driver_id is None:
            load.assign_driver(driver)
        log.log_event("SYSTEM", f"Driver {driver.id} assigned to load")
        log.log_status_transition(LoadStatus.POSTED.value, LoadStatus.ASSIGNED.value)
        load.progress = 0.0
        db.session.commit()  # Commit so map can see the assignment
        
        # Set driver's starting location (25-50 miles from pickup)
        start_lat, start_lng = get_driver_start_location(
            pickup_zip_data["lat"], 
            pickup_zip_data["lng"]
        )
        load.current_lat = start_lat
        load.current_lng = start_lng
        load.last_location_update = datetime.utcnow()
        db.session.commit()  # Commit location update
        
        log.log_event("GPS", f"Driver starting location set: ({start_lat:.4f}, {start_lng:.4f})")
        
        # Step 5: Send intro message
        intro_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="👋 Hi! I've accepted your load. Looking forward to working with you.",
            timestamp=datetime.utcnow()
        )
        db.session.add(intro_msg)
        db.session.commit()
        log.log_message("driver", intro_msg.content)
        time.sleep(1.0)  # Brief pause for message
        
        # Step 6: Progress through statuses with intermediate updates
        # ASSIGNED → NEAR_PICKUP (progress 0.0 → 0.2)
        load.status = LoadStatus.NEAR_PICKUP.value
        log.log_status_transition(LoadStatus.ASSIGNED.value, LoadStatus.NEAR_PICKUP.value)
        
        # Gradually update progress from 0.0 to 0.2 with location updates
        segment_duration = transition_delay
        update_progress_gradually(load, 0.2, segment_duration, update_interval=2.0)
        
        # Update driver location progressively moving toward pickup
        start_progress = 0.0
        end_progress = 0.2
        num_location_updates = max(3, int(segment_duration / 2.0))
        for i in range(num_location_updates):
            progress_ratio = start_progress + (end_progress - start_progress) * (i + 1) / num_location_updates
            # Interpolate between start location and pickup location
            current_lat, current_lng = interpolate_location(
                start_lat, start_lng,
                pickup_zip_data["lat"], pickup_zip_data["lng"],
                progress_ratio / 0.2  # Scale to 0-1 for this segment
            )
            load.current_lat = current_lat
            load.current_lng = current_lng
            load.last_location_update = datetime.utcnow()
            db.session.commit()
            if i < num_location_updates - 1:
                time.sleep(segment_duration / num_location_updates)
        
        # Message: Driver on the way
        msg1 = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="Hi, I'm on the way to pickup. ETA about 30 minutes.",
            timestamp=datetime.utcnow()
        )
        db.session.add(msg1)
        db.session.commit()
        log.log_message("driver", msg1.content)
        time.sleep(1.0)
        
        msg2 = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content="Got it, see you soon!",
            timestamp=datetime.utcnow()
        )
        db.session.add(msg2)
        db.session.commit()
        log.log_message("shipper", msg2.content)
        time.sleep(1.0)
        
        # NEAR_PICKUP → READY (progress 0.2 → 0.4)
        load.status = LoadStatus.READY.value
        log.log_status_transition(LoadStatus.NEAR_PICKUP.value, LoadStatus.READY.value)
        
        # Gradually update progress from 0.2 to 0.4
        segment_duration = transition_delay
        update_progress_gradually(load, 0.4, segment_duration, update_interval=2.0)
        
        # Driver is at/near pickup location
        load.current_lat = pickup_zip_data["lat"] + random.uniform(-0.01, 0.01)
        load.current_lng = pickup_zip_data["lng"] + random.uniform(-0.01, 0.01)
        load.last_location_update = datetime.utcnow()
        db.session.commit()
        
        # Message: Pre-arrival update
        delay_options = ["Running 10 mins late", "Early arrival", "On time"]
        delay_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content=random.choice(delay_options),
            timestamp=datetime.utcnow()
        )
        db.session.add(delay_msg)
        db.session.commit()
        log.log_message("driver", delay_msg.content)
        time.sleep(1.0)
        
        shipper_reply = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content=random.choice(["We're ready", "Dock 3 is open", "Delayed by 15 mins"]),
            timestamp=datetime.utcnow()
        )
        db.session.add(shipper_reply)
        db.session.commit()
        log.log_message("shipper", shipper_reply.content)
        time.sleep(1.0)
        
        # READY → IN_TRANSIT (progress 0.4 → 0.7)
        load.status = LoadStatus.IN_TRANSIT.value
        log.log_status_transition(LoadStatus.READY.value, LoadStatus.IN_TRANSIT.value)
        
        # Gradually update progress from 0.4 to 0.7 with location updates
        segment_duration = transition_delay * 1.5  # Longer segment for transit
        update_progress_gradually(load, 0.7, segment_duration, update_interval=2.0)
        
        # Update driver location progressively moving from pickup toward dropoff
        num_location_updates = max(5, int(segment_duration / 2.0))
        for i in range(num_location_updates):
            progress_ratio = 0.4 + (0.7 - 0.4) * (i + 1) / num_location_updates
            # Interpolate between pickup and dropoff (progress 0.4-0.7 maps to route progress ~0.0-0.5)
            route_progress = (progress_ratio - 0.4) / (0.7 - 0.4) * 0.5  # Scale to 0-0.5 of route
            current_lat, current_lng = interpolate_location(
                pickup_zip_data["lat"], pickup_zip_data["lng"],
                dropoff_zip_data["lat"], dropoff_zip_data["lng"],
                route_progress
            )
            load.current_lat = current_lat
            load.current_lng = current_lng
            load.last_location_update = datetime.utcnow()
            db.session.commit()
            if i < num_location_updates - 1:
                time.sleep(segment_duration / num_location_updates)
        
        log.log_event("GPS", f"Driver in transit: ({load.current_lat:.4f}, {load.current_lng:.4f})")
        
        # Apply idle scenario (already determined earlier)
        if idle_scenario == "idle_15":
            # Simulate idle_15 event
            log.log_event("SYSTEM", "Idle_15 event triggered")
            log.idle_status = "idle_15"
            log.idle_events.append("idle_15")
            
            # Set idle status (if field exists)
            if hasattr(load, 'idle_status'):
                load.idle_status = 'idle_15'
                if hasattr(load, 'last_movement_timestamp'):
                    load.last_movement_timestamp = datetime.utcnow() - timedelta(minutes=16)
                if hasattr(load, 'idle_log'):
                    idle_log = [{
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "idle_15",
                        "resolved_by": None,
                        "notes": "15+ minutes idle, driver can resolve"
                    }]
                    load.idle_log = json.dumps(idle_log)
                db.session.commit()
            else:
                log.log_error("idle_status field not available on Load model", "MISSING_FIELD")
            
            time.sleep(transition_delay * 0.5)
            
            # Driver message explaining delay
            idle_explanations = [
                "Traffic delay, should be moving soon",
                "Engine warning light, checking it out",
                "Rest stop, back on road in 5"
            ]
            idle_msg_content = random.choice(idle_explanations)
            idle_msg = Message(
                load_id=load.id,
                sender_id=driver.id,
                receiver_id=shipper.id,
                content=idle_msg_content,
                timestamp=datetime.utcnow()
            )
            db.session.add(idle_msg)
            db.session.commit()
            log.log_message("driver", idle_msg_content)
            time.sleep(transition_delay * 0.5)
            
            # Resolve idle_15
            if hasattr(load, 'idle_status'):
                load.idle_status = 'active'
                if hasattr(load, 'idle_log'):
                    idle_log = json.loads(load.idle_log) if load.idle_log else []
                    idle_log.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "active",
                        "resolved_by": "driver",
                        "notes": "Resolved by driver"
                    })
                    load.idle_log = json.dumps(idle_log)
                db.session.commit()
                log.log_event("SYSTEM", "Idle_15 resolved by driver")
                log.idle_events.append("idle_15_resolved")
            else:
                log.log_error("Cannot resolve idle_15: field not available", "MISSING_FIELD")
            
        elif idle_scenario == "idle_30":
            # Simulate idle_30 event (requires admin)
            log.log_event("SYSTEM", "Idle_30 event triggered - admin intervention required")
            log.idle_status = "idle_30"
            log.idle_events.append("idle_30")
            
            if hasattr(load, 'idle_status'):
                load.idle_status = 'idle_30'
                if hasattr(load, 'last_movement_timestamp'):
                    load.last_movement_timestamp = datetime.utcnow() - timedelta(minutes=31)
                if hasattr(load, 'idle_log'):
                    idle_log = [{
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "idle_30",
                        "resolved_by": None,
                        "notes": "30+ minutes idle, admin required"
                    }]
                    load.idle_log = json.dumps(idle_log)
                db.session.commit()
            else:
                log.log_error("idle_status field not available on Load model", "MISSING_FIELD")
            
            time.sleep(transition_delay * 0.5)
            
            # Admin message (system message with sender_id=None)
            admin_msg_content = "Please contact shipper immediately. Status check required."
            admin_msg = Message(
                load_id=load.id,
                sender_id=None,  # System message
                receiver_id=driver.id,
                content=admin_msg_content,
                timestamp=datetime.utcnow()
            )
            db.session.add(admin_msg)
            db.session.commit()
            log.log_message("admin", admin_msg_content)
            time.sleep(transition_delay * 0.3)
            
            # Driver response
            driver_response_content = "Back on the road, mechanical issue resolved."
            driver_response = Message(
                load_id=load.id,
                sender_id=driver.id,
                receiver_id=shipper.id,
                content=driver_response_content,
                timestamp=datetime.utcnow()
            )
            db.session.add(driver_response)
            db.session.commit()
            log.log_message("driver", driver_response_content)
            time.sleep(transition_delay * 0.5)
            
            # Resolve idle_30 (admin action)
            if hasattr(load, 'idle_status'):
                load.idle_status = 'active'
                if hasattr(load, 'idle_log'):
                    idle_log = json.loads(load.idle_log) if load.idle_log else []
                    idle_log.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "active",
                        "resolved_by": "admin",
                        "notes": "Resolved by admin"
                    })
                    load.idle_log = json.dumps(idle_log)
                db.session.commit()
                log.log_event("SYSTEM", "Idle_30 resolved by admin")
                log.idle_events.append("idle_30_resolved")
            else:
                log.log_error("Cannot resolve idle_30: field not available", "MISSING_FIELD")
        
        # Step 7: Continue transit to delivery (progress 0.7 → 0.95)
        # Gradually update progress from 0.7 to 0.95 with location updates
        segment_duration = transition_delay * 1.5  # Continue transit
        update_progress_gradually(load, 0.95, segment_duration, update_interval=2.0)
        
        # Update driver location progressively moving from midpoint toward dropoff
        num_location_updates = max(5, int(segment_duration / 2.0))
        for i in range(num_location_updates):
            progress_ratio = 0.7 + (0.95 - 0.7) * (i + 1) / num_location_updates
            # Interpolate between pickup and dropoff (progress 0.7-0.95 maps to route progress ~0.5-0.95)
            route_progress = 0.5 + ((progress_ratio - 0.7) / (0.95 - 0.7)) * 0.45  # Scale to 0.5-0.95 of route
            current_lat, current_lng = interpolate_location(
                pickup_zip_data["lat"], pickup_zip_data["lng"],
                dropoff_zip_data["lat"], dropoff_zip_data["lng"],
                route_progress
            )
            load.current_lat = current_lat
            load.current_lng = current_lng
            load.last_location_update = datetime.utcnow()
            db.session.commit()
            if i < num_location_updates - 1:
                time.sleep(segment_duration / num_location_updates)
        
        # Delivery messages
        arrival_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="I've arrived at the delivery location.",
            timestamp=datetime.utcnow()
        )
        db.session.add(arrival_msg)
        db.session.commit()
        log.log_message("driver", arrival_msg.content)
        time.sleep(1.0)
        
        dock_msg = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content="Dock 3 is open, you can proceed.",
            timestamp=datetime.utcnow()
        )
        db.session.add(dock_msg)
        db.session.commit()
        log.log_message("shipper", dock_msg.content)
        time.sleep(1.0)
        
        # Step 8: Mark as delivered (progress 0.95 → 1.0)
        load.status = LoadStatus.DELIVERED.value
        log.log_status_transition(LoadStatus.IN_TRANSIT.value, LoadStatus.DELIVERED.value)
        
        # Final progress update to 1.0
        update_progress_gradually(load, 1.0, transition_delay * 0.5, update_interval=2.0)
        
        # Update location to dropoff
        load.current_lat = dropoff_zip_data["lat"] + random.uniform(-0.01, 0.01)
        load.current_lng = dropoff_zip_data["lng"] + random.uniform(-0.01, 0.01)
        load.last_location_update = datetime.utcnow()
        load.delivered_at = datetime.utcnow()
        db.session.commit()  # Commit delivery status
        log.log_event("GPS", f"Delivery location reached: ({load.current_lat:.4f}, {load.current_lng:.4f})")
        
        # Apply idle delay if any (extends completion time)
        if idle_delay_seconds > 0:
            log.log_event("SYSTEM", f"Applying idle delay of {idle_delay_seconds:.1f} seconds to completion")
            time.sleep(idle_delay_seconds)
        
        # Step 9: Delivery photo (placeholder)
        delivery_photo_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="Delivery complete! Photo proof attached.",
            photo_url="/static/uploads/messages/delivered_placeholder.jpg",
            timestamp=datetime.utcnow()
        )
        db.session.add(delivery_photo_msg)
        db.session.commit()
        log.log_message("driver", delivery_photo_msg.content)
        log.delivery_photo = True
        
        # Step 10: Create payment (optional)
        try:
            payment = Payment(
                load_id=load.id,
                driver_id=driver.id,
                transaction_id=f"TXN{load.id:06d}",
                amount=estimated_rate,
                driver_payout=estimated_rate * 0.80,  # 80% to driver
                platform_fee=estimated_rate * 0.20,  # 20% platform fee
                status=PaymentStatus.COMPLETED.value,
                payment_method="quick_pay",
                completed_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
        except:
            pass  # Payment model may not be fully configured
        
        # Finalize log
        log.finish(success=True)
        
        # Validate log
        validation = log.validate()
        if not validation["is_healthy"]:
            log.log_error(f"Health check failed: {', '.join(validation['issues'])}", "VALIDATION")
        
        return {
            "load_id": load.id,
            "reference_number": load.reference_number,
            "pickup_zip": pickup_zip,
            "dropoff_zip": dropoff_zip,
            "driver_id": driver.id,
            "idle_events": log.idle_events,
            "status": load.status,
            "health_score": validation["health_score"]
        }
    except Exception as e:
        log.log_error(f"Simulation failed: {str(e)}", "ERROR")
        log.finish(success=False)
        db.session.rollback()
        raise


def create_bulk_shipments(count: int, shippers: List[User] = None, drivers: List[User] = None, total_duration_seconds: float = 300.0) -> Tuple[List[Dict], str]:
    """
    Create multiple simulated shipments concurrently with distance-based durations.
    
    Args:
        count: Number of shipments to create
        shippers: List of shipper users (creates if None)
        drivers: List of driver users (creates if None)
        total_duration_seconds: Not used for concurrent execution (kept for compatibility)
    
    Returns:
        Tuple of (list of shipment details, simulation_run_id)
    """
    global SIMULATION_RUN_ID
    
    # Generate unique run ID
    SIMULATION_RUN_ID = f"SIM_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Get or create test users
    if not shippers:
        shippers = User.query.filter_by(role='shipper').limit(5).all()
        if not shippers:
            # Create a test shipper
            shipper = User(
                email=f"test_shipper_{random.randint(1000, 9999)}@example.com",
                username=f"shipper_{random.randint(1000, 9999)}",
                role='shipper',
                first_name="Test",
                last_name="Shipper",
                company_name="Test Shipping Co",
                is_active=True
            )
            db.session.add(shipper)
            db.session.flush()
            shippers = [shipper]
    
    if not drivers:
        drivers = User.query.filter_by(role='driver').limit(10).all()
        if not drivers:
            # Create a test driver
            driver = User(
                email=f"test_driver_{random.randint(1000, 9999)}@example.com",
                username=f"driver_{random.randint(1000, 9999)}",
                role='driver',
                first_name="Test",
                last_name="Driver",
                is_active=True
            )
            db.session.add(driver)
            db.session.flush()
            drivers = [driver]
    
    # Create all loads first (quickly, no delays)
    loads_data = []
    for i in range(count):
        shipper = random.choice(shippers)
        driver = random.choice(drivers)
        
        # Select pickup and dropoff locations
        pickup_zip_data = get_random_texas_zip()
        dropoff_zip_data = get_random_texas_zip()
        
        # Ensure different locations
        while dropoff_zip_data["zip"] == pickup_zip_data["zip"]:
            dropoff_zip_data = get_random_texas_zip()
        
        # Calculate actual distance
        miles = haversine_distance(
            pickup_zip_data["lat"],
            pickup_zip_data["lng"],
            dropoff_zip_data["lat"],
            dropoff_zip_data["lng"]
        )
        miles = round(miles, 1)
        
        weight = random.randint(500, 28000)
        estimated_rate = calculate_quote(int(miles), weight, pickup_zip_data["zip"], dropoff_zip_data["zip"])
        
        # Create the load
        load = Load(
            reference_number=Load.generate_reference(),
            shipper_id=shipper.id,
            origin_zip=pickup_zip_data["zip"],
            origin_city=pickup_zip_data["city"],
            origin_state="TX",
            origin_lat=pickup_zip_data["lat"],
            origin_lng=pickup_zip_data["lng"],
            destination_zip=dropoff_zip_data["zip"],
            destination_city=dropoff_zip_data["city"],
            destination_state="TX",
            dest_lat=dropoff_zip_data["lat"],
            dest_lng=dropoff_zip_data["lng"],
            distance=int(miles),
            weight=weight,
            rate=estimated_rate,
            equipment_type=random.choice(["dry_van", "flatbed", "reefer", "box_truck"]),
            status=LoadStatus.POSTED.value,
            pickup_date=datetime.utcnow() + timedelta(hours=random.randint(1, 24)),
            created_at=datetime.utcnow()
        )
        db.session.add(load)
        db.session.flush()
        
        # Assign driver immediately
        load.assign_driver(driver)
        db.session.commit()
        
        loads_data.append({
            'load': load,
            'shipper': shipper,
            'driver': driver,
            'shipment_id': i + 1,
            'pickup_zip_data': pickup_zip_data,
            'dropoff_zip_data': dropoff_zip_data
        })
    
    # Start concurrent simulations
    threads = []
    results = []
    results_lock = threading.Lock()
    
    def run_shipment(load_data):
        """Run a single shipment simulation in its own thread with app context."""
        try:
            with current_app.app_context():
                # Run simulation (duration will be calculated from distance)
                shipment = create_simulated_shipment(
                    load_data['shipper'],
                    load_data['driver'],
                    load_data['shipment_id'],
                    SIMULATION_RUN_ID,
                    delay_seconds=None,  # Will be calculated from distance
                    load=load_data['load'],
                    pickup_zip_data=load_data['pickup_zip_data'],
                    dropoff_zip_data=load_data['dropoff_zip_data']
                )
                with results_lock:
                    results.append(shipment)
        except Exception as e:
            # Log error but don't fail entire batch
            with results_lock:
                results.append({
                    "load_id": load_data['load'].id,
                    "error": str(e)
                })
    
    # Start all threads simultaneously
    for load_data in loads_data:
        thread = threading.Thread(target=run_shipment, args=(load_data,))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    return results, SIMULATION_RUN_ID


def generate_simulation_report(run_id: str = None) -> Dict:
    """
    Generate a summary report for a simulation run.
    
    Args:
        run_id: Simulation run ID (uses latest if None)
    
    Returns:
        Dictionary with report data
    """
    if run_id is None:
        # Get latest run ID
        run_ids = set(log.run_id for log in SIMULATION_LOGS.values() if log.run_id)
        if not run_ids:
            return {"error": "No simulation logs found"}
        run_id = max(run_ids)  # Latest by string comparison
    
    # Filter logs by run_id
    run_logs = [log for log in SIMULATION_LOGS.values() if log.run_id == run_id]
    
    if not run_logs:
        return {"error": f"No logs found for run_id: {run_id}"}
    
    # Calculate statistics
    total_shipments = len(run_logs)
    successful = sum(1 for log in run_logs if log.success)
    failed = total_shipments - successful
    
    idle_15_count = sum(1 for log in run_logs if "idle_15" in log.idle_events)
    idle_30_count = sum(1 for log in run_logs if "idle_30" in log.idle_events)
    no_idle_count = total_shipments - idle_15_count - idle_30_count
    
    total_messages = sum(log.message_count for log in run_logs)
    total_errors = sum(len(log.errors) for log in run_logs)
    
    avg_elapsed = sum(
        (log.end_time - log.start_time).total_seconds() 
        for log in run_logs if log.end_time
    ) / total_shipments if total_shipments > 0 else 0
    
    health_scores = [log.validate()["health_score"] for log in run_logs]
    avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0
    
    return {
        "run_id": run_id,
        "start_time": min(log.start_time for log in run_logs).isoformat(),
        "end_time": max(log.end_time for log in run_logs if log.end_time).isoformat() if any(log.end_time for log in run_logs) else None,
        "summary": {
            "total_shipments": total_shipments,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_shipments * 100) if total_shipments > 0 else 0,
            "idle_15_count": idle_15_count,
            "idle_30_count": idle_30_count,
            "no_idle_count": no_idle_count,
            "total_messages": total_messages,
            "total_errors": total_errors,
            "avg_elapsed_seconds": avg_elapsed,
            "avg_health_score": round(avg_health_score, 2)
        },
        "shipments": [log.to_dict() for log in run_logs],
        "shipments_with_validation": [
            {**log.to_dict(), "validation": log.validate()} 
            for log in run_logs
        ]
    }

