#!/usr/bin/env python3
"""End-to-end MVP pipeline.

Flow:
1. Fetch deals from PepperRSSConnector
2. Score each deal using DealScoringEngine
3. Run BestFriendTest to filter qualifying deals
4. Send qualifying deals via TelegramNotifier
"""
import logging
from datetime import datetime

from src.connectors.pepper_rss import PepperRSSConnector
from src.scoring import DealScoringEngine, BestFriendTest, set_action_recommendation
from src.notifiers.telegram import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the complete MVP pipeline."""
    logger.info("=" * 60)
    logger.info("Deal Intelligence Agent - MVP Pipeline")
    logger.info("=" * 60)

    # Step 1: Initialize connector
    logger.info("\n[1/4] Initializing PepperRSSConnector...")
    connector = PepperRSSConnector()

    if not connector.validate():
        logger.error("Connector validation failed. Exiting.")
        return

    # Step 2: Fetch deals
    logger.info("[2/4] Fetching deals from Pepper RSS...")
    deals = connector.fetch_deals()
    logger.info(f"Fetched {len(deals)} deals")

    if not deals:
        logger.warning("No deals fetched. Exiting.")
        return

    # Step 3: Score deals
    logger.info("[3/4] Scoring deals...")
    scored_deals = []
    for deal in deals:
        DealScoringEngine.score_deal(deal)
        set_action_recommendation(deal)
        scored_deals.append(deal)

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


if __name__ == "__main__":
    main()
