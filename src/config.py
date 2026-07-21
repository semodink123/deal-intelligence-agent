"""Configuration management."""
import os
from typing import Optional
from dotenv import load_dotenv
from src.models import UserProfile

load_dotenv()


class Config:
    """Application configuration."""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    
    # Notification thresholds
    IMMEDIATE_THRESHOLD = 95  # Send immediately if score >= 95
    DAILY_DIGEST_THRESHOLD = 90  # Include in daily if score 90-94
    WEEKLY_DIGEST_THRESHOLD = 80  # Include in weekly if score 80-89
    
    # Connectors
    ENABLED_CONNECTORS = ["pepper_rss"]
    
    @staticmethod
    def get_user_profile() -> UserProfile:
        """Load user profile from environment or return default."""
        profile = UserProfile(
            preferred_brands=[
                "Apple",
                "Sony",
                "Nintendo",
                "Samsung",
            ],
            preferred_categories={
                "technology": 1.0,
                "games": 0.8,
                "electronics": 0.9,
                "travel": 0.6,
                "fashion": 0.4,
            },
            preferred_stores=[
                "Amazon",
                "Coolblue",
                "MediaMarkt",
            ],
            interests={
                "gaming": 0.9,
                "tech": 1.0,
                "gadgets": 0.8,
                "deals": 1.0,
            },
            minimum_savings_percentage=10.0,
            minimum_savings_euro=5.0,
        )
        return profile
