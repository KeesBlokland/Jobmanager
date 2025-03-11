# app/utils/profile_utils.py
import os
import json
import logging
from flask import current_app

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
    }
}

class ProfileManager:
    def __init__(self, app=None):
        self.app = app
        self.profile_path = None
        
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
        try:
            if not os.path.exists(self.profile_path):
                self.save_profile(DEFAULT_PROFILE)
                return DEFAULT_PROFILE
            
            with open(self.profile_path, 'r') as f:
                profile = json.load(f)
            return profile
        except Exception as e:
            logger.error(f"Error loading user profile: {str(e)}")
            return DEFAULT_PROFILE
    
    def save_profile(self, profile):
        """Save the user profile."""
        try:
            # Ensure instance directory exists
            os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
            
            with open(self.profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            logger.info("User profile saved successfully")
            return True
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

# Initialize the profile manager
profile_manager = ProfileManager()

def init_app(app):
    """Initialize the profile manager with the Flask app."""
    profile_manager.init_app(app)