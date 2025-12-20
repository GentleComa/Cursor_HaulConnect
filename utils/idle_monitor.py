"""
Idle Monitor

Monitors user sessions and load activity for idle timeout handling.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import session, current_app
from flask_login import current_user


class IdleMonitor:
    """Monitor and manage user idle states."""
    
    DEFAULT_IDLE_TIMEOUT = 1800  # 30 minutes in seconds
    DEFAULT_WARNING_THRESHOLD = 300  # 5 minutes before timeout
    
    def __init__(self, idle_timeout: Optional[int] = None, warning_threshold: Optional[int] = None):
        """
        Initialize idle monitor.
        
        Args:
            idle_timeout: Seconds before session is considered idle
            warning_threshold: Seconds before timeout to show warning
        """
        self.idle_timeout = idle_timeout or self.DEFAULT_IDLE_TIMEOUT
        self.warning_threshold = warning_threshold or self.DEFAULT_WARNING_THRESHOLD
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        session['last_activity'] = datetime.utcnow().isoformat()
    
    def get_last_activity(self) -> Optional[datetime]:
        """Get the last activity timestamp."""
        last_activity = session.get('last_activity')
        if last_activity:
            return datetime.fromisoformat(last_activity)
        return None
    
    def get_idle_duration(self) -> int:
        """Get how long the user has been idle in seconds."""
        last_activity = self.get_last_activity()
        if not last_activity:
            return 0
        
        delta = datetime.utcnow() - last_activity
        return int(delta.total_seconds())
    
    def is_idle(self) -> bool:
        """Check if the user session is idle."""
        return self.get_idle_duration() >= self.idle_timeout
    
    def should_show_warning(self) -> bool:
        """Check if idle warning should be displayed."""
        idle_duration = self.get_idle_duration()
        time_until_timeout = self.idle_timeout - idle_duration
        return 0 < time_until_timeout <= self.warning_threshold
    
    def get_time_until_timeout(self) -> int:
        """Get seconds until session timeout."""
        idle_duration = self.get_idle_duration()
        return max(0, self.idle_timeout - idle_duration)
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete idle status."""
        idle_duration = self.get_idle_duration()
        time_until_timeout = self.get_time_until_timeout()
        
        return {
            'idle_duration': idle_duration,
            'time_until_timeout': time_until_timeout,
            'is_idle': self.is_idle(),
            'show_warning': self.should_show_warning(),
            'timeout_threshold': self.idle_timeout,
            'warning_threshold': self.warning_threshold
        }
    
    def reset(self) -> None:
        """Reset the idle timer."""
        self.update_activity()


class LoadActivityMonitor:
    """Monitor activity on loads for real-time updates."""
    
    def __init__(self):
        self.active_loads: Dict[int, Dict[str, Any]] = {}
    
    def register_viewer(self, load_id: int, user_id: int) -> None:
        """Register a user viewing a load."""
        if load_id not in self.active_loads:
            self.active_loads[load_id] = {
                'viewers': set(),
                'last_update': datetime.utcnow()
            }
        
        self.active_loads[load_id]['viewers'].add(user_id)
        self.active_loads[load_id]['last_update'] = datetime.utcnow()
    
    def unregister_viewer(self, load_id: int, user_id: int) -> None:
        """Unregister a user from viewing a load."""
        if load_id in self.active_loads:
            self.active_loads[load_id]['viewers'].discard(user_id)
            
            # Clean up if no more viewers
            if not self.active_loads[load_id]['viewers']:
                del self.active_loads[load_id]
    
    def get_viewer_count(self, load_id: int) -> int:
        """Get number of users viewing a load."""
        if load_id in self.active_loads:
            return len(self.active_loads[load_id]['viewers'])
        return 0
    
    def is_load_active(self, load_id: int) -> bool:
        """Check if a load has active viewers."""
        return load_id in self.active_loads and len(self.active_loads[load_id]['viewers']) > 0
    
    def cleanup_stale(self, max_age_minutes: int = 30) -> int:
        """Remove stale load entries."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        stale_loads = [
            load_id for load_id, data in self.active_loads.items()
            if data['last_update'] < cutoff
        ]
        
        for load_id in stale_loads:
            del self.active_loads[load_id]
        
        return len(stale_loads)


# Global instance for load activity monitoring
load_activity_monitor = LoadActivityMonitor()

