"""
HaulConnect Utilities

Helper functions and external service integrations.
"""

from utils.freight_quote import FreightQuoteCalculator
from utils.idle_monitor import IdleMonitor
from utils.hubspot import HubSpotClient
from utils.decorators import role_required

__all__ = ['FreightQuoteCalculator', 'IdleMonitor', 'HubSpotClient', 'role_required']

