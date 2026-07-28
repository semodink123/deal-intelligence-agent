"""Pepper RSS connector for fetching deals from the Pepper.nl RSS feed."""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from html import unescape
from typing import List, Optional
from urllib.parse import urlparse

import feedparser

from src.connectors.base import BaseConnector
from src.models import Deal

logger = logging.getLogger(__name__)


class PepperRSSConnector(BaseConnector):
    """Fetch deals from the Pepper.nl RSS feed."""

    DEFAULT_RSS_URL = "https://nl.pepper.com/rss/new"
    MAX_DEAL_AGE_DAYS = 7

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
        """Fetch and parse deals from the Pepper RSS feed."""
        deals: List[Deal] = []

        try:
            logger.info("Fetching deals from Pepper RSS: %s", self.rss_url)
            feed = feedparser.parse(self.rss_url)

            if feed.bozo:
                logger.warning(
                    "Pepper RSS: Feed parsing warning: %s",
                    feed.bozo_exception,
                )

            if not feed.entries:
                logger.warning("Pepper RSS: No entries found in feed")
                return deals

            logger.info("Pepper RSS: Found %d entries", len(feed.entries))

            for entry in feed.entries:
                try:
                    deal = self._parse_entry(entry)
                    if deal:
                        deals.append(deal)
                except Exception:
                    logger.exception("Pepper RSS: Failed to parse entry")

            logger.info("Pepper RSS: Successfully parsed %d deals", len(deals))
            return deals
        except Exception:
            logger.exception("Pepper RSS: Error fetching feed")
            return []

    def _parse_entry(self, entry) -> Optional[Deal]:
        """Parse a single feedparser entry into a Deal object."""
        title = entry.get("title", "").strip()
        link = (entry.get("link") or entry.get("href") or "").strip()
        description = unescape(
            (entry.get("description") or entry.get("summary") or "").strip()
        )

        logger.debug("Pepper RSS entry keys: %s", list(entry.keys()))
        logger.debug("Pepper RSS entry link: %s", link)

        if not title:
            logger.warning("Pepper RSS: Missing title")
            return None
        if not link:
            logger.warning("Pepper RSS: Missing link for entry: %s", title)
            return None

        current_price = self._extract_current_price(title, description)
        if current_price is None:
            logger.warning("Pepper RSS: No current price extracted: %s", title)
            return None

        estimated_normal_price = self._extract_estimated_price(
            title, description, current_price
        )

        store = self._extract_store(title, description)
        category = self._extract_category(title, description)
        brand = self._extract_brand(title)
        deal_id = self._generate_deal_id(link)
        discovered_at = self._parse_published_date(entry)

        cutoff = datetime.utcnow() - timedelta(days=self.MAX_DEAL_AGE_DAYS)
        if discovered_at < cutoff:
            logger.info(
                "Pepper RSS: Skipping old deal (%d days old): %s",
                (datetime.utcnow() - discovered_at).days,
                title,
            )
            return None

        deal = Deal(
            id=deal_id,
            title=title,
            store=store,
            category=category,
            current_price=current_price,
            estimated_normal_price=estimated_normal_price,
            historical_low=current_price * 0.9,
            url=link,
            source="pepper_rss",
            discovered_at=discovered_at,
            brand=brand,
            metadata={
                "description": description,
                "feed": "Pepper.nl",
            },
        )

        logger.debug(
            "Pepper RSS: Parsed deal: %s (EUR %.2f)",
            deal.title,
            deal.current_price,
        )
        return deal

    @staticmethod
    def _price_to_float(value: str) -> Optional[float]:
        """Convert Dutch/international price text to a positive float."""
        cleaned = re.sub(r"[^0-9,.-]", "", value).strip(".-")
        if not cleaned:
            return None

        # If both separators occur, the last one is normally the decimal mark.
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        try:
            price = float(cleaned)
            return price if price >= 0 else None
        except ValueError:
            return None

    def _extract_current_price(
        self, title: str, description: str
    ) -> Optional[float]:
        """Extract the deal price from title and description.

        Pepper normally puts the current price at the start of the summary,
        e.g. ``EUR 13,60 - Bol``. The title is used as a fallback.
        """
        texts = (description, title)
        patterns = (
            r"(?:€|EUR)\s*([0-9]+(?:[.,][0-9]{1,2})?)",
            r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:€|EUR)\b",
        )

        for text in texts:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    price = self._price_to_float(match.group(1))
                    if price is not None:
                        return price
        return None

    def _extract_estimated_price(
        self,
        title: str,
        description: str,
        current_price: float,
    ) -> float:
        """Extract a normal/reference price or estimate it with 20% markup."""
        text = f"{title} {description}"
        label_patterns = (
            r"(?:adviesprijs|normale? prijs|gebruikelijke prijs|reguliere prijs|"
            r"oorspronkelijke prijs|van|in plaats van|rrp|uvp)"
            r"\s*(?:was|is|:|-)?\s*(?:€|EUR)?\s*"
            r"([0-9]+(?:[.,][0-9]{1,2})?)",
            r"(?:€|EUR)\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*"
            r"(?:normaal|regulier|adviesprijs|rrp|uvp)",
        )

        candidates = []
        for pattern in label_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                price = self._price_to_float(match.group(1))
                if price is not None and price > current_price:
                    candidates.append(price)

        if candidates:
            return min(candidates)

        return round(current_price * 1.2, 2)

    def _extract_store(self, title: str, description: str) -> str:
        """Extract the retailer name."""
        known_stores = [
            "Amazon", "Coolblue", "MediaMarkt", "Bol.com", "Bol",
            "Zalando", "Nike", "Adidas", "Booking.com", "eBay",
            "Alibaba", "Joybuy", "Action", "Greetz", "KPN", "Eufy",
        ]
        text = f"{title} {description}".lower()
        for store in known_stores:
            if store.lower() in text:
                return store
        return "Pepper"

    def _extract_category(self, title: str, description: str) -> str:
        """Extract a broad product category."""
        category_keywords = {
            "Electronics": ["phone", "laptop", "tablet", "monitor", "camera", "headphone", "usb-c", "oplader"],
            "Games": ["game", "ps5", "xbox", "nintendo", "steam"],
            "Fashion": ["shirt", "pants", "jacket", "shoes", "dress", "clothing", "legging", "overhemd"],
            "Travel": ["flight", "hotel", "booking", "travel", "reistas"],
            "Books": ["book", "ebook", "kindle"],
            "Home": ["furniture", "kitchen", "bedding", "pillow", "bureau", "fauteuil"],
            "Sports": ["sport", "bike", "fitness", "gym", "loopband"],
        }
        text = f"{title} {description}".lower()
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        return "Other"

    def _extract_brand(self, title: str) -> Optional[str]:
        """Extract a known brand from the title."""
        known_brands = [
            "Apple", "Sony", "Samsung", "LG", "Dell", "HP", "Lenovo",
            "Nike", "Adidas", "Puma", "Canon", "Nikon", "Microsoft",
            "Ugreen", "Eufy", "Eastpak", "Gigabyte", "Therabody",
        ]
        title_lower = title.lower()
        for brand in known_brands:
            if brand.lower() in title_lower:
                return brand
        return None

    def _generate_deal_id(self, url: str) -> str:
        """Generate a stable deal ID from the Pepper URL."""
        try:
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split("/") if part]
            if path_parts:
                numeric_suffix = re.search(r"(\d+)$", path_parts[-1])
                if numeric_suffix:
                    return f"pepper_{numeric_suffix.group(1)}"
        except (TypeError, ValueError):
            pass

        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return f"pepper_{digest}"

    def _parse_published_date(self, entry) -> datetime:
        """Parse the published date, falling back to the current UTC time."""
        try:
            published = entry.get("published_parsed")
            if published:
                return datetime(*published[:6])
            updated = entry.get("updated_parsed")
            if updated:
                return datetime(*updated[:6])
        except (TypeError, ValueError, OverflowError) as exc:
            logger.debug("Pepper RSS: Could not parse date: %s", exc)
        return datetime.utcnow()
