"""Data models for Deal Intelligence Agent."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Classification(str, Enum):
    """Deal classification based on score."""
    LEGENDARY = "Legendary"
    NO_BRAINER = "No Brainer"
    GOD_TIER = "God Tier"
    INSANELY_GOOD = "Insanely Good"
    EXCEPTIONAL = "Exceptional"
    IGNORE = "Ignore"


class ActionRecommendation(str, Enum):
    """Action recommendation for the user."""
    BUY_NOW = "Buy Now"
    STRONGLY_CONSIDER = "Strongly Consider"
    WATCH = "Watch"
    IGNORE = "Ignore"


@dataclass
class Deal:
    """Core deal data structure."""
    id: str
    title: str
    store: str
    category: str
    current_price: float
    estimated_normal_price: float
    historical_low: float
    url: str
    source: str
    discovered_at: datetime
    
    # Calculated fields
    historical_price_score: float = 0.0
    quality_score: float = 0.0
    savings_score: float = 0.0
    scarcity_score: float = 0.0
    personal_relevance_score: float = 0.0
    regret_score: float = 0.0
    final_score: float = 0.0
    
    classification: Optional[Classification] = None
    action_recommendation: Optional[ActionRecommendation] = None
    best_friend_test_passed: bool = False
    
    # Metadata
    brand: Optional[str] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def euro_savings(self) -> float:
        """Calculate savings in euros."""
        return self.estimated_normal_price - self.current_price
    
    @property
    def percentage_savings(self) -> float:
        """Calculate savings as percentage."""
        if self.estimated_normal_price == 0:
            return 0.0
        return (self.euro_savings / self.estimated_normal_price) * 100
    
    @property
    def price_below_historical_low(self) -> bool:
        """Check if current price is below historical low."""
        return self.current_price < self.historical_low


@dataclass
class UserProfile:
    """User preference profile."""
    preferred_brands: list[str] = field(default_factory=list)
    preferred_categories: dict[str, float] = field(default_factory=dict)  # category: relevance_score
    preferred_stores: list[str] = field(default_factory=list)
    interests: dict[str, float] = field(default_factory=dict)  # interest: weight
    minimum_savings_percentage: float = 10.0
    minimum_savings_euro: float = 5.0
    notification_threshold: int = 80
    
    def get_category_relevance(self, category: str) -> float:
        """Get relevance score for a category (0-1)."""
        return self.preferred_categories.get(category.lower(), 0.5)
    
    def get_brand_multiplier(self, brand: str) -> float:
        """Get multiplier for preferred brand (0-2)."""
        if brand.lower() in [b.lower() for b in self.preferred_brands]:
            return 1.5
        return 1.0
    
    def get_store_multiplier(self, store: str) -> float:
        """Get multiplier for preferred store (0-2)."""
        if store.lower() in [s.lower() for s in self.preferred_stores]:
            return 1.3
        return 1.0


@dataclass
class HistoricalPrice:
    """Historical price data for a product."""
    product_id: str
    lowest_price: float
    lowest_price_date: datetime
    average_price: float
    highest_price: float
    samples: int
    last_updated: datetime
