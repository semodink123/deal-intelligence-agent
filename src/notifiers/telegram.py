"""Telegram notifier for sending deal alerts."""
import logging
import os
from typing import Optional

import requests

from src.models import Deal

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends deal notifications via Telegram Bot API."""

    TELEGRAM_API_URL = "https://api.telegram.org/bot"

    def __init__(self):
        """Initialize Telegram notifier from environment variables.

        Reads:
            TELEGRAM_BOT_TOKEN: Bot API token
            TELEGRAM_CHAT_ID: Chat ID to send messages to
        """
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set")
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not set")

    def is_configured(self) -> bool:
        """Check if Telegram notifier is properly configured.

        Returns:
            True if both bot token and chat ID are set.
        """
        return bool(self.bot_token and self.chat_id)

    def send_deal(self, deal: Deal) -> bool:
        """Send a deal notification to Telegram.

        Args:
            deal: Deal object to send

        Returns:
            True if message sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.warning("Telegram notifier not configured, skipping")
            return False

        message = self._format_deal_message(deal)
        return self.send_message(message)

    def send_message(self, text: str) -> bool:
        """Send a plain text message to Telegram.

        Args:
            text: Message text to send

        Returns:
            True if message sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.warning("Telegram notifier not configured")
            return False

        if not text:
            logger.warning("Empty message text")
            return False

        try:
            url = f"{self.TELEGRAM_API_URL}{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text}

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(
                    f"Failed to send Telegram message. Status: {response.status_code}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    def _format_deal_message(self, deal: Deal) -> str:
        """Format a deal into a plain text message.

        Args:
            deal: Deal object to format

        Returns:
            Plain text message string.
        """
        savings_pct = deal.percentage_savings
        savings_eur = deal.euro_savings

        message = (
            f"💰 {deal.title}\n"
            f"Store: {deal.store}\n"
            f"Price: €{deal.current_price:.2f}\n"
            f"Normal: €{deal.estimated_normal_price:.2f}\n"
            f"Save: €{savings_eur:.2f} ({savings_pct:.1f}%)\n"
            f"Category: {deal.category}\n"
            f"Link: {deal.url}"
        )

        return message
