"""Main deal scoring engine orchestrating all subscores."""
from src.models import Deal, UserProfile, Classification, ActionRecommendation
from .historical_price import HistoricalPriceEngine
from .quality import QualityEngine
from .personal_relevance import PersonalRelevanceEngine
from .regret import RegretEngine
from .best_friend_test import BestFriendTest


class DealScoringEngine:
    """Orchestrates all scoring components.
    
    Weights:
    - Historical Price Score: 30%
    - Quality Score: 20%
    - Savings Score: 15%
    - Scarcity Score: 15%
    - Personal Relevance Score: 10%
    - Regret Score: 10%
    """
    
    def __init__(self, user_profile: UserProfile):
        self.profile = user_profile
        self.historical_price = HistoricalPriceEngine()
        self.quality = QualityEngine()
        self.personal_relevance = PersonalRelevanceEngine(user_profile)
        self.regret = RegretEngine()
        self.best_friend = BestFriendTest()
    
    def score_deal(self, deal: Deal) -> Deal:
        """Calculate complete deal score."""
        # Calculate individual scores
        deal.historical_price_score = self.historical_price.calculate_historical_price_score(deal)
        deal.quality_score = self.quality.calculate_quality_score(deal)
        deal.savings_score = self._calculate_savings_score(deal)
        deal.scarcity_score = self._calculate_scarcity_score(deal)
        deal.personal_relevance_score = self.personal_relevance.calculate_personal_relevance_score(deal)
        deal.regret_score = self.regret.calculate_regret_score(deal)
        
        # Calculate final weighted score
        deal.final_score = (
            deal.historical_price_score * 0.30 +
            deal.quality_score * 0.20 +
            deal.savings_score * 0.15 +
            deal.scarcity_score * 0.15 +
            deal.personal_relevance_score * 0.10 +
            deal.regret_score * 0.10
        )
        
        # Run best friend test
        deal.best_friend_test_passed = self.best_friend.run_test(deal)
        
        # Classify deal
        deal.classification = self._classify_deal(deal.final_score)
        
        # Generate action recommendation
        deal.action_recommendation = self._recommend_action(deal)
        
        return deal
    
    def _calculate_savings_score(self, deal: Deal) -> float:
        """Calculate savings score (0-100).
        
        Based on percentage and absolute savings.
        """
        # Start at 50 (baseline)
        score = 50.0
        
        # Percentage component (0-50 points)
        percentage = min(deal.percentage_savings, 50.0)
        score += percentage
        
        # Absolute savings component (bonus for high absolute savings)
        if deal.euro_savings > 50:
            score += 10.0
        elif deal.euro_savings > 20:
            score += 5.0
        
        return min(100.0, score)
    
    def _calculate_scarcity_score(self, deal: Deal) -> float:
        """Calculate scarcity score (0-100).
        
        Estimates how rare/limited this deal is.
        """
        score = 50.0  # Base score
        
        # If below historical low, very scarce
        if deal.price_below_historical_low:
            score += 40.0
        elif deal.current_price < deal.historical_low * 1.1:  # Within 10% of low
            score += 25.0
        elif deal.current_price < deal.historical_low * 1.3:  # Within 30% of low
            score += 15.0
        
        # Time-based scarcity (harder to assess without data)
        if "limited" in deal.title.lower():
            score += 10.0
        
        return min(100.0, score)
    
    @staticmethod
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
    
    def _recommend_action(self, deal: Deal) -> ActionRecommendation:
        """Generate action recommendation."""
        if not deal.best_friend_test_passed:
            return ActionRecommendation.IGNORE
        
        if deal.final_score >= 95:
            return ActionRecommendation.BUY_NOW
        elif deal.final_score >= 85:
            return ActionRecommendation.STRONGLY_CONSIDER
        elif deal.final_score >= 80:
            return ActionRecommendation.WATCH
        else:
            return ActionRecommendation.IGNORE
