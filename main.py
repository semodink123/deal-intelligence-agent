#!/usr/bin/env python3
"""End-to-end MVP pipeline with optional TEST_MODE.

Usage:
    python main.py                    # Normal mode
    python main.py --test             # Test mode with mock data

Execution flow:
1. Fetch deals using PepperRSSConnector
2. Score deals using DealScoringEngine
3. Run BestFriendTest
4. Send qualifying deals to TelegramNotifier
"""
import argparse
import logging
import sys
from datetime import datetime

from src.connectors.pepper_rss import PepperRSSConnector
from src.models import Deal
from src.scoring import DealScoringEngine, BestFriendTest, set_action_recommendation
from src.notifiers.telegram import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_test_deals() -> list[Deal]:
    """Create mock deals for testing pipeline.

    Returns:
        List of test Deal objects.
    """
    test_deals = [
        Deal(
            id="test_001",
            title="Apple MacBook Air M1 - 13 inch",
            store="Amazon",
            category="electronics",
            current_price=799.99,
            estimated_normal_price=999.99,
            historical_low=749.99,
            url="https://example.com/macbook",
            source="test_mode",
            discovered_at=datetime.now(),
            brand="Apple",
        ),
        Deal(
            id="test_002",
            title="Sony WH-1000XM5 Headphones",
            store="Coolblue",
            category="electronics",
            current_price=349.99,
            estimated_normal_price=429.99,
            historical_low=329.99,
            url="https://example.com/headphones",
            source="test_mode",
            discovered_at=datetime.now(),
            brand="Sony",
        ),
        Deal(
            id="test_003",
            title="Generic Budget Smartphone Case",
            store="eBay",
            category="electronics",
            current_price=2.99,
            estimated_normal_price=5.99,
            historical_low=2.50,
            url="https://example.com/case",
            source="test_mode",
            discovered_at=datetime.now(),
            brand=None,
        ),
    ]
    return test_deals


def run_pipeline(deals: list[Deal]) -> None:
    """Run the complete MVP pipeline.

    Args:
        deals: List of Deal objects to process
    """
    if not deals:
        logger.warning("No deals to process. Exiting.")
        return

    # Step 3: Score deals
    logger.info("[3/4] Scoring deals...")
    scored_deals = []
    for deal in deals:
        DealScoringEngine.score_deal(deal)
        set_action_recommendation(deal)
        scored_deals.append(deal)
        logger.info(
            f"  • {deal.title}: {deal.final_score:.1f} "
            f"({deal.classification.value}) - {deal.action_recommendation.value}"
        )

    logger.info(f"Scored {len(scored_deals)} deals")

    # Step 4: Run Best Friend Test
    logger.info("[4/4] Running Best Friend Test...")
    qualifying_deals = [deal for deal in scored_deals if BestFriendTest.run(deal)]

    logger.info(f"✅ {len(qualifying_deals)} deals passed Best Friend Test")

    if not qualifying_deals:
        logger.info("No qualifying deals to send.")
        return

    # Step 5: Send notifications
    logger.info("\n[5/5] Sending Telegram notifications...")
    notifier = TelegramNotifier()

    if not notifier.is_configured():
        logger.warning("Telegram notifier not configured. Skipping notifications.")
        return

    sent_count = 0
    for deal in qualifying_deals:
        if notifier.send_deal(deal):
            sent_count += 1
            logger.info(f"✉️  Sent: {deal.title} (Score: {deal.final_score:.1f})")
        else:
            logger.warning(f"Failed to send: {deal.title}")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Pipeline Complete: {sent_count} notifications sent")
    logger.info(f"{'=' * 60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deal Intelligence Agent MVP Pipeline"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with mock deals (skip RSS fetch)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Deal Intelligence Agent - MVP Pipeline")
    if args.test:
        logger.info("MODE: TEST (using mock data)")
    logger.info("=" * 60)

    if args.test:
        # Test mode: use mock deals
        logger.info("\n[TEST MODE] Creating mock deals...")
        deals = create_test_deals()
        logger.info(f"Created {len(deals)} test deals")
        run_pipeline(deals)
    else:
        # Normal mode: fetch from RSS
        logger.info("\n[1/4] Initializing PepperRSSConnector...")
        connector = PepperRSSConnector()

        if not connector.validate():
            logger.error("Connector validation failed. Exiting.")
            sys.exit(1)

        # Step 2: Fetch deals
        logger.info("[2/4] Fetching deals from Pepper RSS...")
        deals = connector.fetch_deals()
        logger.info(f"Fetched {len(deals)} deals")

        run_pipeline(deals)


if __name__ == "__main__":
    main()
