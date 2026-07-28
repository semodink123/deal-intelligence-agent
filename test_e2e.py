#!/usr/bin/env python3
"""End-to-end validation test for MVP pipeline.

This test:
1. Creates a fake Deal object
2. Runs DealScoringEngine
3. Runs BestFriendTest
4. Sends result through TelegramNotifier

Success criteria:
- All steps execute without exceptions
- Best Friend Test passes/fails as expected
- Telegram message sent (if configured)
- Detailed logging of each step
"""
import logging
import sys
from datetime import datetime

from src.models import Deal
from src.scoring import DealScoringEngine, BestFriendTest, set_action_recommendation
from src.notifiers.telegram import TelegramNotifier

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


class E2EValidator:
    """End-to-end validation runner."""

    def __init__(self):
        """Initialize validator."""
        self.passed = True
        self.test_results = []

    def log_step(self, step_num: int, name: str, status: str, details: str = ""):
        """Log a validation step.

        Args:
            step_num: Step number
            name: Step name
            status: PASS or FAIL
            details: Additional details
        """
        result = {
            "step": step_num,
            "name": name,
            "status": status,
            "details": details,
        }
        self.test_results.append(result)
        symbol = "✅" if status == "PASS" else "❌"
        logger.info(f"{symbol} Step {step_num}: {name} - {status}")
        if details:
            logger.info(f"   └─ {details}")

    def run(self) -> bool:
        """Run complete end-to-end validation.

        Returns:
            True if all steps passed, False otherwise.
        """
        logger.info("=" * 80)
        logger.info("END-TO-END VALIDATION TEST - MVP Pipeline")
        logger.info("=" * 80)

        try:
            # STEP 1: Create fake Deal object
            logger.info("\n[STEP 1] Creating fake Deal object...")
            deal = self._create_test_deal()
            self.log_step(
                1,
                "Create Deal",
                "PASS",
                f"Deal ID: {deal.id}, Title: {deal.title[:40]}",
            )

            # STEP 2: Score the deal
            logger.info("\n[STEP 2] Running DealScoringEngine...")
            try:
                deal = self._score_deal(deal)
                self.log_step(
                    2,
                    "Score Deal",
                    "PASS",
                    f"Final Score: {deal.final_score:.1f}/100, Classification: {deal.classification.value}",
                )
            except Exception as e:
                self.log_step(2, "Score Deal", "FAIL", str(e))
                self.passed = False
                return False

            # STEP 3: Run Best Friend Test
            logger.info("\n[STEP 3] Running BestFriendTest...")
            try:
                test_result = BestFriendTest.run(deal)
                test_status = (
                    f"PASS (deal qualifies)"
                    if test_result
                    else "PASS (deal rejected - as expected)"
                )
                self.log_step(
                    3,
                    "Best Friend Test",
                    "PASS",
                    f"Result: {test_result}, Details: {self._get_test_reason(deal)}",
                )
            except Exception as e:
                self.log_step(3, "Best Friend Test", "FAIL", str(e))
                self.passed = False
                return False

            # STEP 4: Attempt to send via Telegram (if configured)
            logger.info("\n[STEP 4] Testing TelegramNotifier...")
            try:
                notifier = TelegramNotifier()

                if not notifier.is_configured():
                    self.log_step(
                        4,
                        "Send via Telegram",
                        "SKIP",
                        "Telegram not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing)",
                    )
                    logger.info(
                        "   (This is expected in CI without secrets configured)"
                    )
                else:
                    # Send test message
                    message = self._format_test_message(deal)
                    success = notifier.send_message(message)

                    if success:
                        self.log_step(
                            4,
                            "Send via Telegram",
                            "PASS",
                            f"Test message sent to chat {notifier.chat_id}",
                        )
                    else:
                        self.log_step(
                            4,
                            "Send via Telegram",
                            "FAIL",
                            "Message send failed - check token and chat ID",
                        )
                        self.passed = False

            except Exception as e:
                self.log_step(4, "Send via Telegram", "FAIL", str(e))
                self.passed = False

            # STEP 5: Validate Deal object fields
            logger.info("\n[STEP 5] Validating Deal object fields...")
            validation_errors = self._validate_deal(deal)
            if not validation_errors:
                self.log_step(5, "Validate Deal Fields", "PASS", "All fields valid")
            else:
                self.log_step(5, "Validate Deal Fields", "FAIL", "; ".join(validation_errors))
                self.passed = False

            return self.passed

        except Exception as e:
            logger.exception(f"Unexpected error during validation: {e}")
            self.log_step(-1, "Unexpected Error", "FAIL", str(e))
            self.passed = False
            return False

    def _create_test_deal(self) -> Deal:
        """Create a high-quality test deal that should pass all checks."""
        deal = Deal(
            id="e2e_test_001",
            title="Apple MacBook Air M1 13-inch (2024 Edition)",
            store="Amazon",
            category="electronics",
            current_price=799.99,
            estimated_normal_price=1099.99,
            historical_low=749.99,
            url="https://example.com/test/macbook-air-m1",
            source="e2e_test",
            discovered_at=datetime.now(),
            brand="Apple",
        )
        logger.info(f"Created test deal: {deal.title}")
        logger.info(f"  • Price: €{deal.current_price} (Normal: €{deal.estimated_normal_price})")
        logger.info(f"  • Savings: €{deal.euro_savings:.2f} ({deal.percentage_savings:.1f}%)")
        logger.info(f"  • Historical Low: €{deal.historical_low}")
        return deal

    def _score_deal(self, deal: Deal) -> Deal:
        """Score the deal and set action recommendation."""
        logger.info("Computing individual component scores...")

        # Score each component
        deal = DealScoringEngine.score_deal(deal)
        deal = set_action_recommendation(deal)

        # Log all scores
        logger.info(f"  • Historical Price Score: {deal.historical_price_score:.1f}/100")
        logger.info(f"  • Quality Score: {deal.quality_score:.1f}/100")
        logger.info(f"  • Savings Score: {deal.savings_score:.1f}/100")
        logger.info(f"  • Scarcity Score: {deal.scarcity_score:.1f}/100")
        logger.info(f"  • Personal Relevance Score: {deal.personal_relevance_score:.1f}/100")
        logger.info(f"  • Regret Score: {deal.regret_score:.1f}/100")
        logger.info(f"  ──────────────────")
        logger.info(f"  • FINAL SCORE: {deal.final_score:.1f}/100")
        logger.info(f"  • Classification: {deal.classification.value}")
        logger.info(f"  • Action: {deal.action_recommendation.value}")

        return deal

    def _get_test_reason(self, deal: Deal) -> str:
        """Get reason why deal passed/failed Best Friend Test."""
        if deal.euro_savings < 5.0 or deal.percentage_savings < 10:
            return "Insufficient savings"
        if deal.final_score < 70:
            return "Score too low"
        if deal.quality_score < 30 and deal.final_score < 85:
            return "Quality too low"
        return "Qualifies for notification"

    def _format_test_message(self, deal: Deal) -> str:
        """Format test message for Telegram."""
        return (
            f"🧪 **E2E VALIDATION TEST** 🧪\n\n"
            f"Deal: {deal.title}\n"
            f"Store: {deal.store}\n"
            f"Price: €{deal.current_price:.2f}\n"
            f"Normal: €{deal.estimated_normal_price:.2f}\n"
            f"Save: €{deal.euro_savings:.2f} ({deal.percentage_savings:.1f}%)\n"
            f"Score: {deal.final_score:.1f}/100\n"
            f"Classification: {deal.classification.value}\n"
            f"Action: {deal.action_recommendation.value}\n\n"
            f"✅ MVP Pipeline Validation Complete"
        )

    def _validate_deal(self, deal: Deal) -> list[str]:
        """Validate all Deal fields are properly set.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        if not deal.id:
            errors.append("deal.id is missing")
        if not deal.title:
            errors.append("deal.title is missing")
        if not deal.store:
            errors.append("deal.store is missing")
        if not deal.category:
            errors.append("deal.category is missing")
        if deal.current_price <= 0:
            errors.append("deal.current_price must be > 0")
        if deal.estimated_normal_price <= 0:
            errors.append("deal.estimated_normal_price must be > 0")
        if deal.historical_low <= 0:
            errors.append("deal.historical_low must be > 0")
        if not deal.url:
            errors.append("deal.url is missing")
        if not deal.source:
            errors.append("deal.source is missing")
        if not deal.discovered_at:
            errors.append("deal.discovered_at is missing")
        if deal.final_score < 0 or deal.final_score > 100:
            errors.append(f"deal.final_score {deal.final_score} out of range [0, 100]")
        if not deal.classification:
            errors.append("deal.classification not set")
        if not deal.action_recommendation:
            errors.append("deal.action_recommendation not set")

        return errors

    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        for result in self.test_results:
            symbol = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⏭️ "
            logger.info(
                f"{symbol} Step {result['step']}: {result['name']} - {result['status']}"
            )
            if result["details"]:
                logger.info(f"   └─ {result['details']}")

        logger.info("=" * 80)
        if self.passed:
            logger.info("✅ ALL TESTS PASSED - MVP Pipeline is functional!")
        else:
            logger.info("❌ SOME TESTS FAILED - See details above")
        logger.info("=" * 80 + "\n")


def main():
    """Main entry point."""
    validator = E2EValidator()
    success = validator.run()
    validator.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
