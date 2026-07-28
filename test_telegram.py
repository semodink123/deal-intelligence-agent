#!/usr/bin/env python3
"""Test Telegram connectivity using repository secrets.

Usage:
    python test_telegram.py

This script:
1. Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment
2. Sends a test message to verify connectivity
3. Reports success/failure
"""
import logging
import os
import sys

from src.notifiers.telegram import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_telegram():
    """Test Telegram notifier with repository secrets."""
    logger.info("=" * 60)
    logger.info("Telegram Connectivity Test")
    logger.info("=" * 60)

    # Initialize notifier
    notifier = TelegramNotifier()

    # Check if configured
    if not notifier.is_configured():
        logger.error("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        logger.error("Required environment variables:")
        logger.error("  - TELEGRAM_BOT_TOKEN")
        logger.error("  - TELEGRAM_CHAT_ID")
        return False

    logger.info("✅ Environment variables loaded")
    logger.info(f"   Bot Token: {notifier.bot_token[:20]}...")
    logger.info(f"   Chat ID: {notifier.chat_id}")

    # Send test message
    test_message = (
        "🧪 Deal Intelligence Agent - Test Message\n\n"
        "If you see this message, Telegram integration is working correctly!\n\n"
        "This is a connection test from the MVP pipeline."
    )

    logger.info("\n[Sending test message...]")
    success = notifier.send_message(test_message)

    if success:
        logger.info("✅ Test message sent successfully!")
        logger.info("=" * 60)
        return True
    else:
        logger.error("❌ Failed to send test message")
        logger.error("Please verify:")
        logger.error("  - Bot token is valid")
        logger.error("  - Chat ID is correct")
        logger.error("  - Bot has permission to send messages")
        logger.info("=" * 60)
        return False


if __name__ == "__main__":
    success = test_telegram()
    sys.exit(0 if success else 1)
