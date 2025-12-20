"""
Freight Quote Calculator

Calculates freight rates based on origin, destination, equipment, and market conditions.
"""

from dataclasses import dataclass
from typing import Optional
import math


def calculate_quote(miles: int, weight: int, pickup_zip: str, dropoff_zip: str) -> float:
    """
    Calculate freight quote based on mileage, weight, and ZIP codes.
    
    Args:
        miles: Distance in miles (40-400)
        weight: Weight in pounds (500-28000)
        pickup_zip: Pickup ZIP code (used for regional fuel pricing)
        dropoff_zip: Dropoff ZIP code
        
    Returns:
        Estimated total cost in dollars
    """
    # Mock diesel prices based on ZIP prefix
    mock_prices = {
        "90": 5.00, "80": 4.80, "70": 4.60, "60": 4.40,
        "50": 4.20, "40": 4.00, "30": 3.80, "20": 3.60
    }

    pickup_region = pickup_zip[:2] if pickup_zip and len(pickup_zip) >= 2 else "50"
    diesel_price = mock_prices.get(pickup_region, 4.50)

    base_rate = 100  # Base payout to driver
    fuel_cost = (miles / 8.5) * diesel_price
    driver_payout = base_rate + fuel_cost
    total_cost = driver_payout / 0.80  # 20% platform markup

    return max(round(total_cost, 2), 120)  # Minimum quote


@dataclass
class QuoteResult:
    """Freight quote result."""
    estimated_rate: float
    rate_per_mile: float
    distance: int
    equipment_type: str
    fuel_surcharge: float
    base_rate: float
    
    @property
    def total_rate(self):
        return self.estimated_rate + self.fuel_surcharge


class FreightQuoteCalculator:
    """Calculator for freight shipping quotes."""
    
    # Base rates per mile by equipment type
    BASE_RATES = {
        'dry_van': 2.50,
        'flatbed': 3.00,
        'reefer': 3.25,
        'tanker': 3.50,
        'lowboy': 4.00
    }
    
    # Regional multipliers (simplified)
    REGION_MULTIPLIERS = {
        'northeast': 1.15,
        'southeast': 1.00,
        'midwest': 0.95,
        'southwest': 1.05,
        'west': 1.10
    }
    
    # State to region mapping (simplified)
    STATE_REGIONS = {
        'NY': 'northeast', 'MA': 'northeast', 'PA': 'northeast', 'NJ': 'northeast',
        'FL': 'southeast', 'GA': 'southeast', 'NC': 'southeast', 'SC': 'southeast',
        'IL': 'midwest', 'OH': 'midwest', 'MI': 'midwest', 'IN': 'midwest',
        'TX': 'southwest', 'AZ': 'southwest', 'NM': 'southwest', 'OK': 'southwest',
        'CA': 'west', 'WA': 'west', 'OR': 'west', 'NV': 'west', 'CO': 'west'
    }
    
    def __init__(self, fuel_price_per_gallon: float = 4.00):
        self.fuel_price = fuel_price_per_gallon
    
    def calculate_distance(self, origin_state: str, dest_state: str) -> int:
        """
        Estimate distance between states.
        In production, this would use a mapping API.
        """
        # Simplified distance estimation based on state pairs
        # This is a placeholder - real implementation would use Google Maps API
        base_distances = {
            ('CA', 'TX'): 1400,
            ('NY', 'FL'): 1200,
            ('IL', 'CA'): 2000,
            ('TX', 'FL'): 1100,
            ('WA', 'FL'): 3000,
        }
        
        key = tuple(sorted([origin_state, dest_state]))
        return base_distances.get(key, 800)  # Default 800 miles
    
    def get_region(self, state: str) -> str:
        """Get region for a state."""
        return self.STATE_REGIONS.get(state, 'midwest')
    
    def calculate_fuel_surcharge(self, distance: int, mpg: float = 6.5) -> float:
        """Calculate fuel surcharge based on distance and fuel price."""
        gallons_needed = distance / mpg
        base_fuel_cost = gallons_needed * 3.00  # Base fuel price
        current_fuel_cost = gallons_needed * self.fuel_price
        surcharge = max(0, current_fuel_cost - base_fuel_cost)
        return round(surcharge, 2)
    
    def calculate_quote(
        self,
        origin_state: str,
        dest_state: str,
        equipment_type: str = 'dry_van',
        weight: Optional[int] = None,
        distance: Optional[int] = None
    ) -> QuoteResult:
        """
        Calculate a freight quote.
        
        Args:
            origin_state: Origin state code (e.g., 'CA')
            dest_state: Destination state code (e.g., 'TX')
            equipment_type: Type of equipment needed
            weight: Load weight in pounds (optional)
            distance: Distance in miles (optional, will estimate if not provided)
        
        Returns:
            QuoteResult with calculated rates
        """
        # Get or estimate distance
        if distance is None:
            distance = self.calculate_distance(origin_state, dest_state)
        
        # Get base rate per mile
        base_rate_per_mile = self.BASE_RATES.get(equipment_type, 2.50)
        
        # Apply regional multipliers
        origin_region = self.get_region(origin_state)
        dest_region = self.get_region(dest_state)
        avg_multiplier = (
            self.REGION_MULTIPLIERS.get(origin_region, 1.0) +
            self.REGION_MULTIPLIERS.get(dest_region, 1.0)
        ) / 2
        
        # Calculate base rate
        adjusted_rate_per_mile = base_rate_per_mile * avg_multiplier
        base_rate = distance * adjusted_rate_per_mile
        
        # Minimum charge
        base_rate = max(base_rate, 350)
        
        # Weight adjustment (heavier loads cost more)
        if weight and weight > 30000:
            weight_factor = 1 + ((weight - 30000) / 100000)
            base_rate *= weight_factor
        
        # Calculate fuel surcharge
        fuel_surcharge = self.calculate_fuel_surcharge(distance)
        
        # Final rate
        estimated_rate = round(base_rate, 2)
        rate_per_mile = round(estimated_rate / distance, 2) if distance > 0 else 0
        
        return QuoteResult(
            estimated_rate=estimated_rate,
            rate_per_mile=rate_per_mile,
            distance=distance,
            equipment_type=equipment_type,
            fuel_surcharge=fuel_surcharge,
            base_rate=round(base_rate, 2)
        )

