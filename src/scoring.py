"""Minimal scoring engines for MVP.

These are temporary mock implementations to be replaced with real engines.
"""
import logging
from typing import Optional

from src.models import Deal, Classification, ActionRecommendation

logger = logging.getLogger(__name__)


class DealScoringEngine:
    """Calculate deal scores using weighted component scores."""

    # Weights for score components (must sum to 1.0)
    WEIGHTS = {
        "historical_price": 0.30,
        "quality": 0.20,
        "savings": 0.15,
        "scarcity": 0.15,
        "personal_relevance": 0.10,
        "regret": 0.10,
    }

    @staticmethod
    def calculate_historical_price_score(deal: Deal) -> float:
        """Score based on price vs historical low.

        Returns 0-100.
        """
        if deal.historical_low <= 0:
            return 50.0

        # If current price is below historical low, perfect score
        if deal.current_price < deal.historical_low:
            return 100.0

        # If current price equals historical low, very high score
        if deal.current_price == deal.historical_low:
            return 95.0

        # Otherwise, score based on percentage above historical low
        pct_above = ((deal.current_price - deal.historical_low) / deal.historical_low) * 100
        if pct_above > 50:
            return 0.0
        return max(0, 100 - (pct_above * 2))

    @staticmethod
    def calculate_quality_score(deal: Deal) -> float:
        """Score based on brand recognition (mock).

        Returns 0-100.
        """
        # Mock: Known brands get higher scores
        known_brands = [
            "Apple",
            "Sony",
            "Samsung",
            "Nike",
            "Adidas",
            "Dell",
            "HP",
            "Lenovo",
            "Microsoft",
        ]

        if deal.brand and deal.brand.lower() in [b.lower() for b in known_brands]:
            return 80.0
        return 50.0

    @staticmethod
    def calculate_savings_score(deal: Deal) -> float:
        """Score based on absolute and percentage savings.

        Returns 0-100.
        """
        pct_savings = deal.percentage_savings

        # Minimum €5 savings threshold
        if deal.euro_savings < 5.0:
            return 0.0

        # Score based on percentage savings
        if pct_savings >= 50:
            return 100.0
        if pct_savings >= 30:
            return 85.0
        if pct_savings >= 20:
            return 70.0
        if pct_savings >= 10:
            return 50.0
        return max(0, pct_savings * 5)

    @staticmethod
    def calculate_scarcity_score(deal: Deal) -> float:
        """Score based on rarity (mock).

        Returns 0-100.
        """
        # Mock: Assume moderate scarcity
        # In production: track deal frequency, time available, stock levels
        return 50.0

    @staticmethod
    def calculate_personal_relevance_score(deal: Deal) -> float:
        """Score based on category/brand/store preferences (mock).

        Returns 0-100.
        """
        # Mock: No user profile yet, return neutral
        return 50.0

    @staticmethod
    def calculate_regret_score(deal: Deal) -> float:
        """Score how much user would regret missing this deal.

        Returns 0-100.
        """
        # Mock: Based on savings and product type
        pct_savings = deal.percentage_savings
        category_multiplier = 1.0

        # Electronics have higher regret potential
        if deal.category.lower() in ["electronics", "games"]:
            category_multiplier = 1.5

        regret = min(100, pct_savings * category_multiplier)
        return regret

    @staticmethod
    def score_deal(deal: Deal) -> Deal:
        """Calculate all scores and final score for a deal.

        Updates deal in-place and returns it.
        """
        # Calculate component scores
        deal.historical_price_score = DealScoringEngine.calculate_historical_price_score(deal)
        deal.quality_score = DealScoringEngine.calculate_quality_score(deal)
        deal.savings_score = DealScoringEngine.calculate_savings_score(deal)
        deal.scarcity_score = DealScoringEngine.calculate_scarcity_score(deal)
        deal.personal_relevance_score = (
            DealScoringEngine.calculate_personal_relevance_score(deal)
        )
        deal.regret_score = DealScoringEngine.calculate_regret_score(deal)

        # Calculate weighted final score
        deal.final_score = (
            deal.historical_price_score * DealScoringEngine.WEIGHTS["historical_price"]
            + deal.quality_score * DealScoringEngine.WEIGHTS["quality"]
            + deal.savings_score * DealScoringEngine.WEIGHTS["savings"]
            + deal.scarcity_score * DealScoringEngine.WEIGHTS["scarcity"]
            + deal.personal_relevance_score * DealScoringEngine.WEIGHTS["personal_relevance"]
            + deal.regret_score * DealScoringEngine.WEIGHTS["regret"]
        )

        # Classify based on final score
        deal.classification = _classify_deal(deal.final_score)

        return deal


class BestFriendTest:
    """Test: Would an extreme value expert recommend this deal to a best friend?"""

    @staticmethod
    def run(deal: Deal) -> bool:
        """Run the best friend test.

        Returns True if deal passes (should be recommended), False otherwise.
        """
        # Test 1: Must have minimum savings
        if deal.euro_savings < 5.0 or deal.percentage_savings < 10:
            logger.debug(f"Best Friend Test FAIL (savings): {deal.title}")
            return False

        # Test 2: Must have reasonable final score
        if deal.final_score < 50:
            logger.debug(f"Best Friend Test FAIL (score): {deal.title} - {deal.final_score}")
            return False

        # Test 3: Quality check - must have brand or high quality
        if deal.quality_score < 30 and deal.final_score < 85:
            logger.debug(f"Best Friend Test FAIL (quality): {deal.title}")
            return False

        logger.debug(f"Best Friend Test PASS: {deal.title} ({deal.final_score:.1f})")
        deal.best_friend_test_passed = True
        return True


def _classify_deal(score: float) -> Classification:
    """Classify deal based on score."""
    if score >= 100:
        return Classification.LEGENDARY
    elif score >= 95:
        return Classification.NO_BRAINER
    elif score >= 90:
        return Classification.GOD_TIER
    elif score >= 85:
        return Classification.INSANELY_GOOD
    elif score >= 80:
        return Classification.EXCEPTIONAL
    else:
        return Classification.IGNORE


def set_action_recommendation(deal: Deal) -> Deal:
    """Set action recommendation based on classification and score."""
    if deal.final_score >= 95:
        deal.action_recommendation = ActionRecommendation.BUY_NOW
    elif deal.final_score >= 85:
        deal.action_recommendation = ActionRecommendation.STRONGLY_CONSIDER
    elif deal.final_score >= 75:
        deal.action_recommendation = ActionRecommendation.WATCH
    else:
        deal.action_recommendation = ActionRecommendation.IGNORE

    return deal
