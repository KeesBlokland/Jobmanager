# app/utils/profile_utils.py
import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger('jobmanager')

DEFAULT_PROFILE = {
    "business_name": "Your Business Name",
    "address": {
        "street": "Your Street Address",
        "city": "Your City",
        "postal_code": "Your Postal Code",
        "country": "DE"
    },
    "contact": {
        "email": "your.email@example.com",
        "phone": "+49 123 456789"
    },
    "tax_info": {
        "is_small_business": True,
        "vat_id": ""
    },
    "banking": {
        "account_holder": "Your Name",
        "iban": "DE...",
        "bic": "..."
    },
    "preferences": {
        "time_offset_minutes": 0  # Default to UTC
    }
}

class ProfileManager:
    def __init__(self, app=None):
        self.app = app
        self.profile_path = None
        self._profile_cache = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the profile manager with a Flask app."""
        self.app = app
        
        # Set profile path in instance directory
        self.profile_path = os.path.join(app.instance_path, 'user_profile.json')
        
        # Ensure the profile exists
        if not os.path.exists(self.profile_path):
            self.save_profile(DEFAULT_PROFILE)
            logger.info(f"Created default user profile at {self.profile_path}")
    
    def get_profile(self):
        """Get the user profile."""
        # Always read fresh from disk to avoid caching issues
        self._profile_cache = None
            
        try:
            if not os.path.exists(self.profile_path):
                self.save_profile(DEFAULT_PROFILE)
                return DEFAULT_PROFILE
            
            with open(self.profile_path, 'r') as f:
                profile = json.load(f)
            
            # Ensure preferences exist
            if 'preferences' not in profile:
                profile['preferences'] = {'time_offset_minutes': 0}
            elif 'time_offset_minutes' not in profile['preferences']:
                profile['preferences']['time_offset_minutes'] = 0
                
            # Cache profile
            self._profile_cache = profile
            return profile
        except Exception as e:
            logger.error(f"Error loading user profile: {str(e)}")
            return DEFAULT_PROFILE
    
    def get_time_offset_minutes(self):
        """Get the user's time offset in minutes."""
        try:
            profile = self.get_profile()
            offset = profile.get('preferences', {}).get('time_offset_minutes', 0)
            
            logger.info(f"Using time offset: {offset} minutes")
            return offset
        except Exception as e:
            logger.error(f"Error getting time offset: {str(e)}")
            return 0
            
    def save_profile(self, profile):
        """Save the user profile with last modified timestamp."""
        try:
            # Add last modified timestamp
            profile['last_modified'] = datetime.now().isoformat()
            
            # Ensure preferences exist
            if 'preferences' not in profile:
                profile['preferences'] = {'time_offset_minutes': 0}
            
            # Ensure instance directory exists
            if self.profile_path:
                os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
                
                with open(self.profile_path, 'w') as f:
                    json.dump(profile, f, indent=2)
                logger.info(f"User profile saved with time offset: {profile['preferences']['time_offset_minutes']}")
                
                # Update cache
                self._profile_cache = profile
                
                return True
            else:
                logger.error("Profile path not set")
                return False
        except Exception as e:
            logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    def update_profile(self, updates):
        """Update specific fields in the profile."""
        current_profile = self.get_profile()
        
        # Update top-level fields
        for key, value in updates.items():
            if key in current_profile:
                if isinstance(value, dict) and isinstance(current_profile[key], dict):
                    # If it's a nested dictionary, update the nested fields
                    current_profile[key].update(value)
                else:
                    # Otherwise replace the value
                    current_profile[key] = value
        
        return self.save_profile(current_profile)

# Create a singleton instance
profile_manager = ProfileManager()

def init_app(app):
    """Initialize the profile manager with the Flask app."""
    global profile_manager
    profile_manager.init_app(app)