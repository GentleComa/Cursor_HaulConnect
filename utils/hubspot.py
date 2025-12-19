"""
HubSpot Integration

Client for HubSpot CRM integration for lead management and marketing automation.
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class HubSpotContact:
    """HubSpot contact data."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    hubspot_id: Optional[str] = None


class HubSpotClient:
    """Client for HubSpot API integration."""
    
    BASE_URL = 'https://api.hubapi.com'
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize HubSpot client.
        
        Args:
            api_key: HubSpot API key (falls back to HUBSPOT_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('HUBSPOT_API_KEY')
        self._enabled = bool(self.api_key)
    
    @property
    def is_enabled(self) -> bool:
        """Check if HubSpot integration is enabled."""
        return self._enabled
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a request to the HubSpot API.
        
        In production, this would use the requests library.
        This is a stub for development.
        """
        if not self.is_enabled:
            return {'status': 'disabled', 'message': 'HubSpot integration not configured'}
        
        # Stub response for development
        return {
            'status': 'success',
            'endpoint': endpoint,
            'method': method,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def create_contact(self, contact: HubSpotContact) -> Dict[str, Any]:
        """
        Create a new contact in HubSpot.
        
        Args:
            contact: HubSpotContact object with contact details
        
        Returns:
            API response with created contact data
        """
        data = {
            'properties': {
                'email': contact.email,
                'firstname': contact.first_name,
                'lastname': contact.last_name,
                'phone': contact.phone,
                'company': contact.company,
                'haulconnect_role': contact.role
            }
        }
        
        return self._make_request('POST', '/crm/v3/objects/contacts', data)
    
    def update_contact(self, hubspot_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing contact.
        
        Args:
            hubspot_id: HubSpot contact ID
            properties: Properties to update
        
        Returns:
            API response
        """
        data = {'properties': properties}
        return self._make_request('PATCH', f'/crm/v3/objects/contacts/{hubspot_id}', data)
    
    def get_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a contact by email address.
        
        Args:
            email: Email address to search
        
        Returns:
            Contact data or None if not found
        """
        result = self._make_request('GET', f'/crm/v3/objects/contacts/email/{email}')
        
        if result.get('status') == 'success':
            return result
        return None
    
    def track_event(self, email: str, event_name: str, properties: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Track a custom event for a contact.
        
        Args:
            email: Contact email
            event_name: Name of the event (e.g., 'load_posted', 'load_booked')
            properties: Additional event properties
        
        Returns:
            API response
        """
        data = {
            'email': email,
            'eventName': event_name,
            'properties': properties or {},
            'occurredAt': datetime.utcnow().isoformat()
        }
        
        return self._make_request('POST', '/events/v3/send', data)
    
    def sync_user(self, user) -> Dict[str, Any]:
        """
        Sync a HaulConnect user to HubSpot.
        
        Args:
            user: User model instance
        
        Returns:
            API response
        """
        contact = HubSpotContact(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            company=getattr(user, 'company_name', None),
            role=user.role
        )
        
        # Check if contact exists
        existing = self.get_contact_by_email(user.email)
        
        if existing and existing.get('hubspot_id'):
            # Update existing contact
            return self.update_contact(
                existing['hubspot_id'],
                {
                    'firstname': contact.first_name,
                    'lastname': contact.last_name,
                    'phone': contact.phone,
                    'company': contact.company,
                    'haulconnect_role': contact.role,
                    'haulconnect_verified': str(user.is_verified).lower()
                }
            )
        else:
            # Create new contact
            return self.create_contact(contact)
    
    def track_load_posted(self, user, load) -> Dict[str, Any]:
        """Track when a user posts a load."""
        return self.track_event(
            user.email,
            'load_posted',
            {
                'load_id': load.id,
                'reference': load.reference_number,
                'origin': f'{load.origin_city}, {load.origin_state}',
                'destination': f'{load.destination_city}, {load.destination_state}',
                'rate': float(load.rate)
            }
        )
    
    def track_load_booked(self, driver, load) -> Dict[str, Any]:
        """Track when a driver books a load."""
        return self.track_event(
            driver.email,
            'load_booked',
            {
                'load_id': load.id,
                'reference': load.reference_number,
                'rate': float(load.rate)
            }
        )
    
    def track_load_delivered(self, driver, load, payment) -> Dict[str, Any]:
        """Track when a load is delivered."""
        return self.track_event(
            driver.email,
            'load_delivered',
            {
                'load_id': load.id,
                'reference': load.reference_number,
                'payment_amount': float(payment.driver_payout)
            }
        )


# Global client instance
hubspot_client = HubSpotClient()

