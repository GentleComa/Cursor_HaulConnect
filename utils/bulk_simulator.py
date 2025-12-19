"""
Bulk Shipment Simulator

Creates and simulates multiple test shipments with full lifecycle,
messaging, idle alerts, and status progression.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from extensions import db
from models.user import User
from models.load import Load, LoadStatus
from models.message import Message
from models.payment import Payment, PaymentStatus
from utils.freight_quote import calculate_quote


# Global simulation logs storage
SIMULATION_LOGS = {}
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


def create_simulated_shipment(shipper: User, driver: User, shipment_id: int, run_id: str = None) -> Dict:
    """
    Create a single simulated shipment with full lifecycle.
    
    Returns:
        Dict with shipment details including load_id and simulation results
    """
    # Initialize log entry
    log = SimulationLogEntry(shipment_id, driver.id, shipper.id, run_id)
    log.log_event("SYSTEM", "Starting shipment simulation")
    
    try:
        # Step 1: Select pickup and dropoff locations
        pickup_zip_data = get_random_texas_zip()
        dropoff_zip_data = get_random_texas_zip()
        
        # Ensure different locations
        while dropoff_zip_data["zip"] == pickup_zip_data["zip"]:
            dropoff_zip_data = get_random_texas_zip()
        
        pickup_zip = pickup_zip_data["zip"]
        dropoff_zip = dropoff_zip_data["zip"]
        
        log.origin_zip = pickup_zip
        log.destination_zip = dropoff_zip
        log.log_event("SYSTEM", f"Selected route: {pickup_zip} → {dropoff_zip}")
        
        # Step 2: Calculate distance and quote
        miles = random.randint(40, 400)
        weight = random.randint(500, 28000)
        
        estimated_rate = calculate_quote(miles, weight, pickup_zip, dropoff_zip)
        
        # Step 3: Create the load
        load = Load(
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
            distance=miles,
            weight=weight,
            rate=estimated_rate,
            equipment_type=random.choice(["dry_van", "flatbed", "reefer", "box_truck"]),
            status=LoadStatus.POSTED.value,
            pickup_date=datetime.utcnow() + timedelta(hours=random.randint(1, 24)),
            created_at=datetime.utcnow()
        )
        db.session.add(load)
        db.session.flush()  # Get load.id
        
        # Store log in global dict
        SIMULATION_LOGS[load.id] = log
        
        log.log_event("SYSTEM", f"Created load {load.reference_number}")
        log.log_status_transition("none", LoadStatus.POSTED.value)
        
        # Step 4: Assign driver
        load.assign_driver(driver)
        log.log_event("SYSTEM", f"Driver {driver.id} assigned to load")
        log.log_status_transition(LoadStatus.POSTED.value, LoadStatus.ASSIGNED.value)
        
        # Set driver's starting location (25-50 miles from pickup)
        start_lat, start_lng = get_driver_start_location(
            pickup_zip_data["lat"], 
            pickup_zip_data["lng"]
        )
        load.current_lat = start_lat
        load.current_lng = start_lng
        load.last_location_update = datetime.utcnow()
        
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
        log.log_message("driver", intro_msg.content)
        
        # Step 6: Progress through statuses
        # accepted → near_pickup
        load.status = LoadStatus.NEAR_PICKUP.value
        load.last_updated = datetime.utcnow()
        load.progress = 0.2
        log.log_status_transition(LoadStatus.ASSIGNED.value, LoadStatus.NEAR_PICKUP.value)
        
        # Message: Driver on the way
        msg1 = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="Hi, I'm on the way to pickup. ETA about 30 minutes.",
            timestamp=datetime.utcnow() + timedelta(minutes=5)
        )
        db.session.add(msg1)
        log.log_message("driver", msg1.content)
        
        msg2 = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content="Got it, see you soon!",
            timestamp=datetime.utcnow() + timedelta(minutes=6)
        )
        db.session.add(msg2)
        log.log_message("shipper", msg2.content)
        
        # near_pickup → ready
        load.status = LoadStatus.READY.value
        load.last_updated = datetime.utcnow() + timedelta(minutes=10)
        load.progress = 0.4
        log.log_status_transition(LoadStatus.NEAR_PICKUP.value, LoadStatus.READY.value)
        
        # Message: Pre-arrival update
        delay_options = ["Running 10 mins late", "Early arrival", "On time"]
        delay_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content=random.choice(delay_options),
            timestamp=datetime.utcnow() + timedelta(minutes=15)
        )
        db.session.add(delay_msg)
        log.log_message("driver", delay_msg.content)
        
        shipper_reply = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content=random.choice(["We're ready", "Dock 3 is open", "Delayed by 15 mins"]),
            timestamp=datetime.utcnow() + timedelta(minutes=16)
        )
        db.session.add(shipper_reply)
        log.log_message("shipper", shipper_reply.content)
        
        # ready → in_transit
        load.status = LoadStatus.IN_TRANSIT.value
        load.last_updated = datetime.utcnow() + timedelta(minutes=20)
        load.progress = 0.7
        log.log_status_transition(LoadStatus.READY.value, LoadStatus.IN_TRANSIT.value)
        
        # Update driver location to be near pickup
        load.current_lat = pickup_zip_data["lat"] + random.uniform(-0.01, 0.01)
        load.current_lng = pickup_zip_data["lng"] + random.uniform(-0.01, 0.01)
        load.last_location_update = datetime.utcnow() + timedelta(minutes=20)
        log.log_event("GPS", f"Driver location updated: ({load.current_lat:.4f}, {load.current_lng:.4f})")
        
        # Determine idle scenario (20% idle_15, 5% idle_30, 75% no issues)
        idle_scenario = random.choices(
            ["none", "idle_15", "idle_30"],
            weights=[75, 20, 5]
        )[0]
        
        if idle_scenario == "idle_15":
            # Simulate idle_15 event
            idle_time = datetime.utcnow() + timedelta(minutes=25)
            log.log_event("SYSTEM", "Idle_15 event triggered")
            log.idle_status = "idle_15"
            log.idle_events.append("idle_15")
            
            # Set idle status (if field exists)
            if hasattr(load, 'idle_status'):
                load.idle_status = 'idle_15'
                if hasattr(load, 'last_movement_timestamp'):
                    load.last_movement_timestamp = idle_time - timedelta(minutes=16)
                if hasattr(load, 'idle_log'):
                    idle_log = [{
                        "timestamp": idle_time.isoformat(),
                        "status": "idle_15",
                        "resolved_by": None,
                        "notes": "15+ minutes idle, driver can resolve"
                    }]
                    load.idle_log = json.dumps(idle_log)
            else:
                log.log_error("idle_status field not available on Load model", "MISSING_FIELD")
            
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
                timestamp=idle_time
            )
            db.session.add(idle_msg)
            log.log_message("driver", idle_msg_content)
            
            # Resolve idle_15
            if hasattr(load, 'idle_status'):
                load.idle_status = 'active'
                if hasattr(load, 'idle_log'):
                    idle_log = json.loads(load.idle_log) if load.idle_log else []
                    idle_log.append({
                        "timestamp": (idle_time + timedelta(minutes=1)).isoformat(),
                        "status": "active",
                        "resolved_by": "driver",
                        "notes": "Resolved by driver"
                    })
                    load.idle_log = json.dumps(idle_log)
                log.log_event("SYSTEM", "Idle_15 resolved by driver")
                log.idle_events.append("idle_15_resolved")
            else:
                log.log_error("Cannot resolve idle_15: field not available", "MISSING_FIELD")
            
        elif idle_scenario == "idle_30":
            # Simulate idle_30 event (requires admin)
            idle_time = datetime.utcnow() + timedelta(minutes=30)
            log.log_event("SYSTEM", "Idle_30 event triggered - admin intervention required")
            log.idle_status = "idle_30"
            log.idle_events.append("idle_30")
            
            if hasattr(load, 'idle_status'):
                load.idle_status = 'idle_30'
                if hasattr(load, 'last_movement_timestamp'):
                    load.last_movement_timestamp = idle_time - timedelta(minutes=31)
                if hasattr(load, 'idle_log'):
                    idle_log = [{
                        "timestamp": idle_time.isoformat(),
                        "status": "idle_30",
                        "resolved_by": None,
                        "notes": "30+ minutes idle, admin required"
                    }]
                    load.idle_log = json.dumps(idle_log)
            else:
                log.log_error("idle_status field not available on Load model", "MISSING_FIELD")
            
            # Admin message (system message with sender_id=None)
            admin_msg_content = "Please contact shipper immediately. Status check required."
            admin_msg = Message(
                load_id=load.id,
                sender_id=None,  # System message
                receiver_id=driver.id,
                content=admin_msg_content,
                timestamp=idle_time + timedelta(minutes=1)
            )
            db.session.add(admin_msg)
            log.log_message("admin", admin_msg_content)
            
            # Driver response
            driver_response_content = "Back on the road, mechanical issue resolved."
            driver_response = Message(
                load_id=load.id,
                sender_id=driver.id,
                receiver_id=shipper.id,
                content=driver_response_content,
                timestamp=idle_time + timedelta(minutes=2)
            )
            db.session.add(driver_response)
            log.log_message("driver", driver_response_content)
            
            # Resolve idle_30 (admin action)
            if hasattr(load, 'idle_status'):
                load.idle_status = 'active'
                if hasattr(load, 'idle_log'):
                    idle_log = json.loads(load.idle_log) if load.idle_log else []
                    idle_log.append({
                        "timestamp": (idle_time + timedelta(minutes=3)).isoformat(),
                        "status": "active",
                        "resolved_by": "admin",
                        "notes": "Resolved by admin"
                    })
                    load.idle_log = json.dumps(idle_log)
                log.log_event("SYSTEM", "Idle_30 resolved by admin")
                log.idle_events.append("idle_30_resolved")
            else:
                log.log_error("Cannot resolve idle_30: field not available", "MISSING_FIELD")
        
        # Step 7: Delivery messages
        delivery_time = datetime.utcnow() + timedelta(minutes=45)
        
        arrival_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="I've arrived at the delivery location.",
            timestamp=delivery_time
        )
        db.session.add(arrival_msg)
        log.log_message("driver", arrival_msg.content)
        
        dock_msg = Message(
            load_id=load.id,
            sender_id=shipper.id,
            receiver_id=driver.id,
            content="Dock 3 is open, you can proceed.",
            timestamp=delivery_time + timedelta(minutes=1)
        )
        db.session.add(dock_msg)
        log.log_message("shipper", dock_msg.content)
        
        # Step 8: Mark as delivered
        load.status = LoadStatus.DELIVERED.value
        load.delivered_at = delivery_time + timedelta(minutes=5)
        load.last_updated = delivery_time + timedelta(minutes=5)
        load.progress = 1.0
        log.log_status_transition(LoadStatus.IN_TRANSIT.value, LoadStatus.DELIVERED.value)
        
        # Update location to dropoff
        load.current_lat = dropoff_zip_data["lat"] + random.uniform(-0.01, 0.01)
        load.current_lng = dropoff_zip_data["lng"] + random.uniform(-0.01, 0.01)
        load.last_location_update = delivery_time + timedelta(minutes=5)
        log.log_event("GPS", f"Delivery location reached: ({load.current_lat:.4f}, {load.current_lng:.4f})")
        
        # Step 9: Delivery photo (placeholder)
        delivery_photo_msg = Message(
            load_id=load.id,
            sender_id=driver.id,
            receiver_id=shipper.id,
            content="Delivery complete! Photo proof attached.",
            photo_url="/static/uploads/messages/delivered_placeholder.jpg",
            timestamp=delivery_time + timedelta(minutes=6)
        )
        db.session.add(delivery_photo_msg)
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
                completed_at=delivery_time + timedelta(minutes=10)
            )
            db.session.add(payment)
        except:
            pass  # Payment model may not be fully configured
        
        db.session.commit()
        
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


def create_bulk_shipments(count: int, shippers: List[User] = None, drivers: List[User] = None) -> Tuple[List[Dict], str]:
    """
    Create multiple simulated shipments.
    
    Args:
        count: Number of shipments to create
        shippers: List of shipper users (creates if None)
        drivers: List of driver users (creates if None)
    
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
    
    shipments = []
    
    for i in range(count):
        shipper = random.choice(shippers)
        driver = random.choice(drivers)
        
        shipment = create_simulated_shipment(shipper, driver, i + 1, SIMULATION_RUN_ID)
        shipments.append(shipment)
    
    return shipments, SIMULATION_RUN_ID


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

