---
name: Concurrent Distance-Based Simulation
overview: Modify the bulk simulation to run shipments concurrently with distance-based durations and idle event delays. Each shipment will calculate its actual distance between pickup/dropoff and use a tiered duration system. Idle events will add delays to completion time.
todos:
  - id: add_haversine
    content: Add haversine_distance() function to calculate actual miles between pickup/dropoff coordinates
    status: completed
  - id: add_duration_calc
    content: Add calculate_duration_from_distance() function with tiered mapping (short/medium/long distances)
    status: completed
  - id: update_shipment_creation
    content: Modify create_simulated_shipment() to use actual distance calculation instead of random distance
    status: completed
    dependencies:
      - add_haversine
  - id: implement_idle_delays
    content: "Add idle delay tracking: +30s for idle_15 events, +45s for idle_30 events, and apply to total duration"
    status: completed
  - id: update_duration_logic
    content: Update create_simulated_shipment() to calculate base duration from distance tier and add idle delays before calculating transition_delay
    status: completed
    dependencies:
      - add_duration_calc
      - implement_idle_delays
  - id: implement_concurrency
    content: Refactor create_bulk_shipments() to use threading.Thread for concurrent shipment execution with proper Flask app contexts
    status: completed
    dependencies:
      - update_shipment_creation
      - update_duration_logic
  - id: test_concurrent_simulation
    content: Test that multiple shipments run concurrently, durations are distance-based, and idle delays extend completion times
    status: completed
    dependencies:
      - implement_concurrency
  - id: add_intermediate_progress
    content: Add intermediate progress state updates between major status changes (e.g., 0.0 → 0.05 → 0.1 → 0.15 → 0.2)
    status: completed
    dependencies:
      - implement_concurrency
  - id: add_realtime_updates
    content: Commit progress and location updates frequently (every 2-3 seconds) so map/dashboard shows changes in real-time
    status: completed
    dependencies:
      - add_intermediate_progress
  - id: add_progressive_location
    content: Update driver GPS coordinates progressively along route (interpolate between pickup and dropoff locations)
    status: completed
    dependencies:
      - add_intermediate_progress
---

# Concurrent Distance-Based Bulk Simulation

## Overview

Transform the bulk simulation from sequential to concurrent execution, with duration based on actual distance between pickup and dropoff locations, plus idle event delays.

## Changes Required

### 1. Add Haversine Distance Calculation

**File**: `utils/bulk_simulator.py`Add a function to calculate actual distance between two lat/lng coordinates:

```python
import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in miles between two lat/lng coordinates."""
    # Haversine formula implementation
```



### 2. Calculate Actual Distance and Duration

**File**: `utils/bulk_simulator.py`In `create_simulated_shipment()`:

- Replace random distance generation with actual haversine calculation using pickup/dropoff coordinates
- Implement tiered duration mapping:
- Short distances (<100 miles): 30-45 seconds base duration
- Medium distances (100-200 miles): 45-60 seconds base duration  
- Long distances (>200 miles): 60-90 seconds base duration
- Track idle delays separately and add them to total duration

### 3. Add Idle Delay Tracking

**File**: `utils/bulk_simulator.py`Modify idle event handling:

- When `idle_15` occurs: add 30 seconds to the shipment's total duration
- When `idle_30` occurs: add 45 seconds to the shipment's total duration
- Apply these delays at the end of the simulation timeline

### 4. Implement Concurrent Execution

**File**: `utils/bulk_simulator.py`Modify `create_bulk_shipments()` to:

- Use Python's `threading.Thread` to run each shipment simulation concurrently
- Create all loads first (quickly, no delays)
- Start all shipment threads simultaneously
- Use thread-safe database sessions (each thread gets its own `db.session`)
- Collect results from all threads using `threading.Thread.join()`

**Key considerations**:

- Each thread needs its own Flask app context: `with app.app_context():`
- Database sessions must be thread-local
- Use `threading.Lock` if needed for shared resources like `SIMULATION_LOGS`

### 5. Update Duration Calculation Logic

**File**: `utils/bulk_simulator.py`In `create_simulated_shipment()`:

- Calculate base duration from distance tier
- Track idle delays separately
- Adjust `transition_delay` based on total duration (base + idle delays)
- Ensure status transitions are spread proportionally across the total duration

## Implementation Details

### Distance-to-Duration Mapping

```python
def calculate_duration_from_distance(miles: float) -> float:
    """Calculate base duration in seconds based on distance."""
    if miles < 100:
        return random.uniform(30, 45)  # Short: 30-45s
    elif miles < 200:
        return random.uniform(45, 60)  # Medium: 45-60s
    else:
        return random.uniform(60, 90)  # Long: 60-90s
```



### Concurrent Execution Pattern

```python
import threading
from flask import current_app

def create_bulk_shipments(...):
    # Create all loads first (no delays)
    loads = []
    for i in range(count):
        # Create load, assign driver, commit
        loads.append(load)
    
    # Start concurrent simulations
    threads = []
    results = []
    lock = threading.Lock()
    
    def run_shipment(load, shipper, driver, shipment_id):
        with current_app.app_context():
            # Run simulation with distance-based duration
            result = create_simulated_shipment(...)
            with lock:
                results.append(result)
    
    for load in loads:
        thread = threading.Thread(target=run_shipment, args=(...))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads
    for thread in threads:
        thread.join()
```



### Idle Delay Application

- Track idle events during simulation
- Calculate total idle delay: `idle_15_count * 30 + idle_30_count * 45`
- Add this delay to the base duration before calculating `transition_delay`
- Apply delays proportionally across remaining transitions

## Files to Modify

1. **`utils/bulk_simulator.py`**

- Add `haversine_distance()` function
- Add `calculate_duration_from_distance()` function
- Modify `create_simulated_shipment()` to use actual distance and tiered durations
- Add idle delay tracking and application
- Modify `create_bulk_shipments()` for concurrent execution with threading
- Add intermediate progress state updates with frequent database commits
- Add progressive driver location updates along routes

### 6. Add Intermediate Progress States and Real-Time Updates

**File**: `utils/bulk_simulator.py`Modify `create_simulated_shipment()` to:

- Update progress incrementally between major status changes (e.g., 0.0 → 0.05 → 0.1 → 0.15 → 0.2)
- Commit progress updates to database frequently (every 2-3 seconds) so map/dashboard can see changes in real-time
- Update driver location progressively along the route (interpolate between pickup and dropoff)
- Ensure status changes are immediately visible on the map by committing after each update

**Implementation approach**:

- Break down each major status transition into smaller progress increments
- Use a loop to gradually update progress from current to target value
- Commit to database after each progress increment
- Update driver GPS coordinates to show movement along the route
- Use smaller sleep intervals (1-2 seconds) between progress updates

## Testing Considerations

- Verify all shipments start concurrently (check timestamps)
- Verify distance-based durations are applied correctly