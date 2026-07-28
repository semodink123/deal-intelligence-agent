"""Evidence-aware deal scoring for the MVP pipeline.

The scorer deliberately treats generated fallback prices as unknown rather than
as proof of savings. This prevents neutral or weak deals from passing the
Best Friend Test solely because the connector supplied estimates.
"""

import logging
import math
from typing import Optional

from src.models import ActionRecommendation, Classification, Deal

logger = logging.getLogger(__name__)


class DealScoringEngine:
    """Calculate an evidence-aware score between 0 and 100."""

    WEIGHTS = {
        "historical_price": 0.20,
        "quality": 0.15,
        "savings": 0.35,
        "scarcity": 0.10,
        "personal_relevance": 0.10,
        "regret": 0.10,
    }

    KNOWN_BRANDS = {
        "apple", "sony", "samsung", "nike", "adidas", "dell", "hp",
        "lenovo", "microsoft", "philips", "lego", "puma", "eufy",
        "ugreen", "gigabyte", "eastpak", "therabody", "xiaomi",
    }

    @staticmethod
    def _valid_number(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )

    @staticmethod
    def _approximately(left: float, right: float, tolerance: float = 0.01) -> bool:
        return abs(left - right) <= max(tolerance, abs(right) * 0.001)

    @classmethod
    def has_real_reference_price(cls, deal: Deal) -> bool:
        """Return False when the normal price looks like the 20% fallback."""
        current = getattr(deal, "current_price", None)
        normal = getattr(deal, "estimated_normal_price", None)
        if not cls._valid_number(current) or not cls._valid_number(normal):
            return False
        if current <= 0 or normal <= current:
            return False

        # pepper_rss uses current_price * 1.20 when no reference price exists.
        if cls._approximately(normal, round(current * 1.20, 2)):
            return False
        return True

    @classmethod
    def has_real_historical_low(cls, deal: Deal) -> bool:
        """Return False for missing data and the connector's 90% placeholder."""
        current = getattr(deal, "current_price", None)
        historical = getattr(deal, "historical_low", None)
        if not cls._valid_number(current) or not cls._valid_number(historical):
            return False
        if current <= 0 or historical <= 0:
            return False

        # pepper_rss currently uses current_price * 0.90 as a placeholder.
        return not cls._approximately(historical, current * 0.90)

    @classmethod
    def calculate_historical_price_score(cls, deal: Deal) -> float:
        """Score price versus a genuine historical low; unknown is neutral."""
        if not cls.has_real_historical_low(deal):
            return 50.0

        current = deal.current_price
        historical = deal.historical_low
        ratio = current / historical
        if ratio <= 0.95:
            return 100.0
        if ratio <= 1.00:
            return 95.0
        if ratio >= 1.50:
            return 0.0
        return max(0.0, 95.0 - ((ratio - 1.0) / 0.50) * 95.0)

    @classmethod
    def calculate_quality_score(cls, deal: Deal) -> float:
        """Use modest brand confidence; do not confuse fame with deal quality."""
        brand = (getattr(deal, "brand", None) or "").strip().lower()
        return 75.0 if brand in cls.KNOWN_BRANDS else 50.0

    @classmethod
    def calculate_savings_score(cls, deal: Deal) -> float:
        """Score verified savings continuously instead of in large buckets."""
        if not cls.has_real_reference_price(deal):
            return 0.0

        euro_savings = max(0.0, float(deal.euro_savings))
        pct_savings = max(0.0, min(100.0, float(deal.percentage_savings)))
        if euro_savings < 2.0 or pct_savings < 5.0:
            return 0.0

        # Percentage is primary. Absolute savings adds at most 15 points.
        percentage_component = min(85.0, pct_savings * 1.7)
        absolute_component = min(15.0, euro_savings / 5.0)
        return min(100.0, percentage_component + absolute_component)

    @staticmethod
    def calculate_scarcity_score(deal: Deal) -> float:
        """Use explicit urgency evidence from the feed description."""
        metadata = getattr(deal, "metadata", {}) or {}
        text = f"{deal.title} {metadata.get('description', '')}".lower()

        strong = ("laatste stuks", "nog 1", "nog 2", "nog 3", "op=op")
        moderate = ("tijdelijk", "alleen vandaag", "t/m", "tot en met", "voorraad")
        if any(term in text for term in strong):
            return 80.0
        if any(term in text for term in moderate):
            return 65.0
        return 40.0

    @staticmethod
    def calculate_personal_relevance_score(deal: Deal) -> float:
        """Stay neutral until an actual preference profile is available."""
        return 50.0

    @classmethod
    def calculate_regret_score(cls, deal: Deal) -> float:
        """Estimate regret only when the discount has supporting evidence."""
        if not cls.has_real_reference_price(deal):
            return 0.0

        savings = cls.calculate_savings_score(deal)
        category = (getattr(deal, "category", "") or "").lower()
        multiplier = 1.10 if category in {"electronics", "games"} else 1.0
        return min(100.0, savings * multiplier)

    @classmethod
    def score_deal(cls, deal: Deal) -> Deal:
        """Populate component scores, final score, classification and action."""
        deal.historical_price_score = cls.calculate_historical_price_score(deal)
        deal.quality_score = cls.calculate_quality_score(deal)
        deal.savings_score = cls.calculate_savings_score(deal)
        deal.scarcity_score = cls.calculate_scarcity_score(deal)
        deal.personal_relevance_score = cls.calculate_personal_relevance_score(deal)
        deal.regret_score = cls.calculate_regret_score(deal)

        deal.final_score = sum(
            (
                deal.historical_price_score * cls.WEIGHTS["historical_price"],
                deal.quality_score * cls.WEIGHTS["quality"],
                deal.savings_score * cls.WEIGHTS["savings"],
                deal.scarcity_score * cls.WEIGHTS["scarcity"],
                deal.personal_relevance_score * cls.WEIGHTS["personal_relevance"],
                deal.regret_score * cls.WEIGHTS["regret"],
            )
        )
        deal.final_score = max(0.0, min(100.0, deal.final_score))
        deal.classification = _classify_deal(deal.final_score)
        set_action_recommendation(deal)

        logger.info(
            "%s | Historical=%.1f | Quality=%.1f | Savings=%.1f | "
            "Scarcity=%.1f | Relevance=%.1f | Regret=%.1f | Final=%.1f | "
            "Reference=%s | HistoricalEvidence=%s",
            deal.title,
            deal.historical_price_score,
            deal.quality_score,
            deal.savings_score,
            deal.scarcity_score,
            deal.personal_relevance_score,
            deal.regret_score,
            deal.final_score,
            "real" if cls.has_real_reference_price(deal) else "unknown/estimated",
            "real" if cls.has_real_historical_low(deal) else "unknown/estimated",
        )
        return deal


class BestFriendTest:
    """Only recommend deals supported by savings evidence and a strong score."""

    MIN_FINAL_SCORE = 65.0
    MIN_PERCENTAGE_SAVINGS = 15.0
    MIN_EURO_SAVINGS = 5.0

    @classmethod
    def run(cls, deal: Deal) -> bool:
        deal.best_friend_test_passed = False

        if not DealScoringEngine.has_real_reference_price(deal):
            logger.debug("Best Friend Test FAIL (unverified reference): %s", deal.title)
            return False
        if deal.euro_savings < cls.MIN_EURO_SAVINGS:
            logger.debug("Best Friend Test FAIL (absolute savings): %s", deal.title)
            return False
        if deal.percentage_savings < cls.MIN_PERCENTAGE_SAVINGS:
            logger.debug("Best Friend Test FAIL (percentage savings): %s", deal.title)
            return False
        if deal.final_score < cls.MIN_FINAL_SCORE:
            logger.debug(
                "Best Friend Test FAIL (score %.1f < %.1f): %s",
                deal.final_score,
                cls.MIN_FINAL_SCORE,
                deal.title,
            )
            return False
        if deal.quality_score < 40.0:
            logger.debug("Best Friend Test FAIL (quality): %s", deal.title)
            return False

        deal.best_friend_test_passed = True
        logger.debug("Best Friend Test PASS: %s (%.1f)", deal.title, deal.final_score)
        return True


def _classify_deal(score: float) -> Classification:
    """Map only genuinely exceptional scores to promotional labels."""
    if score >= 95:
        return Classification.LEGENDARY
    if score >= 90:
        return Classification.NO_BRAINER
    if score >= 85:
        return Classification.GOD_TIER
    if score >= 80:
        return Classification.INSANELY_GOOD
    if score >= 75:
        return Classification.EXCEPTIONAL
    return Classification.IGNORE


def set_action_recommendation(deal: Deal) -> Deal:
    """Set a practical action independently from the marketing label."""
    if deal.final_score >= 90:
        deal.action_recommendation = ActionRecommendation.BUY_NOW
    elif deal.final_score >= 75:
        deal.action_recommendation = ActionRecommendation.STRONGLY_CONSIDER
    elif deal.final_score >= 65:
        deal.action_recommendation = ActionRecommendation.WATCH
    else:
        deal.action_recommendation = ActionRecommendation.IGNORE
    return deal
