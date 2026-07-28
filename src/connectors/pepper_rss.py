"""Pepper RSS connector for fetching deals from Pepper.pl RSS feed."""
import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
import feedparser

from src.models import Deal
from src.connectors.base import BaseConnector
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PepperRSSConnector(BaseConnector):
    """Fetches deals from Pepper.nl RSS feed.
    
    Pepper is a European deals aggregator platform.
    RSS feed contains: title, price, description, link.
    """
    
    DEFAULT_RSS_URL = "https://nl.pepper.com/rss/new"
    
    def __init__(self, config: dict = None):
        super().__init__(name="pepper_rss", config=config or {})
        self.rss_url = self.config.get("url", self.DEFAULT_RSS_URL)
        self.timeout = self.config.get("timeout", 10)
        
    def validate(self) -> bool:
        """Validate connector configuration."""
        if not self.rss_url:
            logger.error("Pepper RSS: Missing RSS URL in config")
            return False
        return True
    
    def fetch_deals(self) -> List[Deal]:
        """Fetch deals from Pepper RSS feed.
        
        Returns:
            List of Deal objects parsed from RSS entries.
        """
        deals = []
        
        try:
            logger.info(f"Fetching deals from Pepper RSS: {self.rss_url}")
            feed = feedparser.parse(self.rss_url)
            
            if feed.bozo:
                logger.warning(f"Pepper RSS: Feed parsing warning: {feed.bozo_exception}")
            
            if not feed.entries:
                logger.warning("Pepper RSS: No entries found in feed")
                return deals
            
            logger.info(f"Pepper RSS: Found {len(feed.entries)} entries")
            
            for entry in feed.entries:
                try:
                    deal = self._parse_entry(entry)
                    if deal:
                        deals.append(deal)
                except Exception as e:
                    logger.warning(f"Pepper RSS: Failed to parse entry: {e}")
                    continue
            
            logger.info(f"Pepper RSS: Successfully parsed {len(deals)} deals")
            return deals
            
        except Exception as e:
            logger.error(f"Pepper RSS: Error fetching feed: {e}")
            return []
    
    def _parse_entry(self, entry) -> Optional[Deal]:
        """Parse a single RSS entry into a Deal object.
        
        Args:
            entry: feedparser RSS entry
            
        Returns:
            Deal object or None if parsing fails.
        """
        try:
            # Extract basic fields
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            description = entry.get("description", "").strip()
            
            if not title or not link:
                logger.debug("Pepper RSS: Skipping entry without title or link")
                return None
            
            # Parse prices from title and description
            current_price = self._extract_current_price(title, description)
            estimated_normal_price = self._extract_estimated_price(description)

            if current_price is None:
                logger.debug(f"Pepper RSS: Could not extract current price for: {title}")
                return None

            # Estimate normal price if not found (20% markup)
            if estimated_normal_price is None:
                estimated_normal_price = current_price * 1.2
            
            # Extract metadata
            store = self._extract_store(title, description)
            category = self._extract_category(title, description)
            brand = self._extract_brand(title)
            
            # Generate deal ID from URL
            deal_id = self._generate_deal_id(link)
            
            # Parse discovery time
            discovered_at = self._parse_published_date(entry)

            # Skip old deals
            MAX_DEAL_AGE_DAYS = 7

            if discovered_at < datetime.utcnow() - timedelta(days=MAX_DEAL_AGE_DAYS):
                logger.info(
                    f"Pepper RSS: Skipping old deal ({(datetime.utcnow() - discovered_at).days} days old): {title}"
                )
                return None
            
            # Create Deal object
            deal = Deal(
                id=deal_id,
                title=title,
                store=store,
                category=category,
                current_price=current_price,
                estimated_normal_price=estimated_normal_price,
                historical_low=current_price * 0.9,  # Estimate: 90% of current price
                url=link,
                source="pepper_rss",
                discovered_at=discovered_at,
                brand=brand,
                metadata={
                    "description": description,
                    "feed": "Pepper.nl",
                }
            )
            
            logger.debug(f"Pepper RSS: Parsed deal: {deal.title} (€{deal.current_price})")
            return deal
            
        except Exception as e:
            logger.warning(f"Pepper RSS: Error parsing entry: {e}")
            return None
    
    def _extract_current_price(self, title: str, description: str) -> Optional[float]:
        """Extract current price from title or description.
        
        Looks for patterns like "€19.99", "19.99€", "19,99€", etc.
        """
        # Try title first, then description
        for text in [title, description]:
            price = self._extract_price_from_text(text)
            if price is not None:
                return price
        return None
    
    def _extract_estimated_price(self, description: str) -> Optional[float]:
        """Extract estimated normal price from description.
        
        Looks for patterns like "normal price €29.99", "regular €29.99", etc.
        If not found, estimates as current_price * 1.2 (20% markup).
        """
        patterns = [
            r"(?:normal|regular|list|rrp|uvp)[^\d]*[€$]?\s*([0-9]+[.,][0-9]{2})",
            r"[€$]\s*([0-9]+[.,][0-9]{2})[^\d]*(?:normal|regular|list|rrp|uvp)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(",", ".")
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        return None  # Let caller estimate if needed
    
    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Extract a price value from text using regex.
        
        Handles formats like: €19.99, 19.99€, €19,99, 19,99€
        """
        if not text:
            return None
        
        # Match prices with € or $ symbol
        pattern = r"[€$]?\s*([0-9]+[.,][0-9]{2})\s*[€$]?"
        match = re.search(pattern, text)
        
        if match:
            price_str = match.group(1).replace(",", ".")
            try:
                return float(price_str)
            except ValueError:
                pass
        
        return None
    
    def _extract_store(self, title: str, description: str) -> str:
        """Extract store/retailer name from title or description.
        
        Common Pepper.nl stores: Amazon, Coolblue, MediaMarkt, bol.com, etc.
        """
        known_stores = [
            "Amazon", "Coolblue", "MediaMarkt", "Bol.com", "Zalando",
            "Nike", "Adidas", "Booking.com", "eBay", "Alibaba",
        ]
        
        text = f"{title} {description}".lower()
        
        for store in known_stores:
            if store.lower() in text:
                return store
        
        return "Pepper"  # Default to Pepper if store not recognized
    
    def _extract_category(self, title: str, description: str) -> str:
        """Extract product category from title or description.
        
        Categories: Electronics, Gaming, Fashion, Travel, Books, Home, etc.
        """
        category_keywords = {
            "electronics": ["phone", "laptop", "tablet", "monitor", "camera", "headphone"],
            "games": ["game", "ps5", "xbox", "nintendo", "steam"],
            "fashion": ["shirt", "pants", "jacket", "shoes", "dress", "clothing"],
            "travel": ["flight", "hotel", "flight", "booking", "travel"],
            "books": ["book", "ebook", "kindle"],
            "home": ["furniture", "kitchen", "bedding", "pillow"],
            "sports": ["sport", "bike", "fitness", "gym"],
        }
        
        text = f"{title} {description}".lower()
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category.capitalize()
        
        return "Other"  # Default category
    
    def _extract_brand(self, title: str) -> Optional[str]:
        """Extract brand name from title.
        
        Common brands: Apple, Sony, Samsung, Nike, Adidas, etc.
        """
        known_brands = [
            "Apple", "Sony", "Samsung", "LG", "Dell", "HP", "Lenovo",
            "Nike", "Adidas", "Puma", "Canon", "Nikon", "Microsoft",
        ]
        
        for brand in known_brands:
            if brand.lower() in title.lower():
                return brand
        
        return None
    
    def _generate_deal_id(self, url: str) -> str:
        """Generate a unique deal ID from URL.
        
        Uses URL path to ensure consistency.
        """
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            
            if path_parts:
                deal_id = path_parts[-1]
                if deal_id.isdigit():
                    return f"pepper_{deal_id}"
            
            # Fallback: use hash of URL
            return f"pepper_{hash(url) % 10**8}"
        except Exception:
            return f"pepper_{hash(url) % 10**8}"
    
    def _parse_published_date(self, entry) -> datetime:
        """Parse published date from RSS entry.
        
        Returns current time if parsing fails.
        """
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception as e:
            logger.debug(f"Pepper RSS: Could not parse date: {e}")
        
        return datetime.utcnow()
