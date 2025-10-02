"""
Push notification service for bridge transaction updates.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound

from data.models import Alert, BridgeSession, Transaction


logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications to users."""

    def __init__(self, bot: Bot):
        """
        Initialize notification service.

        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot

    async def notify_session_created(
        self,
        user_id: int,
        session: BridgeSession,
    ) -> bool:
        """
        Notify user about new bridge session creation.

        Args:
            user_id: Telegram user ID
            session: Created bridge session

        Returns:
            True if notification sent successfully
        """
        message = (
            "🆕 <b>Bridge Session Created</b>\n\n"
            f"Session ID: <code>{session.session_id}</code>\n"
            f"Direction: {session.direction.replace('_to_', ' → ')}\n"
            f"Token: {session.token}\n"
            f"Amount: {session.amount}\n\n"
            f"We'll notify you when transaction status changes!"
        )

        return await self._send_notification(user_id, message)

    async def notify_transaction_detected(
        self,
        user_id: int,
        session: BridgeSession,
        transaction: Transaction,
    ) -> bool:
        """
        Notify user about detected transaction.

        Args:
            user_id: Telegram user ID
            session: Bridge session
            transaction: Detected transaction

        Returns:
            True if notification sent successfully
        """
        message = (
            "🔍 <b>Transaction Detected</b>\n\n"
            f"Session: <code>{session.session_id[:16]}...</code>\n"
            f"Chain: {transaction.chain.upper()}\n"
            f"Hash: <code>{transaction.hash[:16]}...{transaction.hash[-8:]}</code>\n\n"
            f"Status: Waiting for confirmations...\n"
            f"Required: {transaction.confirmations_required}"
        )

        return await self._send_notification(user_id, message)

    async def notify_confirmation_progress(
        self,
        user_id: int,
        session: BridgeSession,
        transaction: Transaction,
        milestone: bool = False,
    ) -> bool:
        """
        Notify user about confirmation progress.

        Args:
            user_id: Telegram user ID
            session: Bridge session
            transaction: Transaction being confirmed
            milestone: True if this is a milestone update (25%, 50%, 75%)

        Returns:
            True if notification sent successfully
        """
        confirmations = transaction.confirmations
        required = transaction.confirmations_required
        progress = (confirmations / required * 100) if required > 0 else 0

        # Only send milestone updates to avoid spam
        if not milestone and progress not in (25, 50, 75):
            return True

        progress_bar = self._generate_progress_bar(progress)

        message = (
            "⏳ <b>Confirmation Progress</b>\n\n"
            f"Session: <code>{session.session_id[:16]}...</code>\n"
            f"Chain: {transaction.chain.upper()}\n\n"
            f"{progress_bar}\n"
            f"Confirmations: {confirmations}/{required}\n"
            f"Progress: {progress:.0f}%"
        )

        return await self._send_notification(user_id, message)

    async def notify_transaction_confirmed(
        self,
        user_id: int,
        session: BridgeSession,
        transaction: Transaction,
        side: str = "source",
    ) -> bool:
        """
        Notify user about transaction confirmation.

        Args:
            user_id: Telegram user ID
            session: Bridge session
            transaction: Confirmed transaction
            side: Which side of bridge (source/destination)

        Returns:
            True if notification sent successfully
        """
        message = (
            "✅ <b>Transaction Confirmed!</b>\n\n"
            f"Session: <code>{session.session_id[:16]}...</code>\n"
            f"Chain: {transaction.chain.upper()}\n"
            f"Side: {side.title()}\n\n"
            f"Confirmations: {transaction.confirmations}/{transaction.confirmations_required}\n\n"
        )

        if side == "source":
            message += (
                "🔄 Bridge is now processing your transaction.\n"
                "Destination transaction will appear in 1-5 minutes."
            )
        else:
            message += (
                "🎉 Bridge completed successfully!\n"
                "Your tokens should now be in your destination wallet."
            )

        return await self._send_notification(user_id, message)

    async def notify_transaction_failed(
        self,
        user_id: int,
        session: BridgeSession,
        transaction: Transaction,
        error: Optional[str] = None,
    ) -> bool:
        """
        Notify user about transaction failure.

        Args:
            user_id: Telegram user ID
            session: Bridge session
            transaction: Failed transaction
            error: Error message

        Returns:
            True if notification sent successfully
        """
        message = (
            "❌ <b>Transaction Failed</b>\n\n"
            f"Session: <code>{session.session_id[:16]}...</code>\n"
            f"Chain: {transaction.chain.upper()}\n"
            f"Hash: <code>{transaction.hash[:16]}...{transaction.hash[-8:]}</code>\n\n"
        )

        if error:
            message += f"<b>Error:</b> {error}\n\n"

        message += (
            "<b>Common Issues:</b>\n"
            "• Insufficient gas/fees\n"
            "• Token approval not set\n"
            "• Network congestion\n\n"
            "Use /status to diagnose the issue."
        )

        return await self._send_notification(user_id, message)

    async def notify_bridge_completed(
        self,
        user_id: int,
        session: BridgeSession,
    ) -> bool:
        """
        Notify user about completed bridge session.

        Args:
            user_id: Telegram user ID
            session: Completed bridge session

        Returns:
            True if notification sent successfully
        """
        message = (
            "🎉 <b>Bridge Session Completed!</b>\n\n"
            f"Session: <code>{session.session_id}</code>\n"
            f"Direction: {session.direction.replace('_to_', ' → ')}\n"
            f"Token: {session.token}\n"
            f"Amount: {session.amount}\n\n"
            f"✅ Tokens successfully bridged!\n"
            f"Check your destination wallet to confirm receipt."
        )

        return await self._send_notification(user_id, message)

    async def notify_bridge_stuck(
        self,
        user_id: int,
        session: BridgeSession,
        reason: str,
    ) -> bool:
        """
        Notify user about stuck bridge session.

        Args:
            user_id: Telegram user ID
            session: Stuck bridge session
            reason: Reason why it's stuck

        Returns:
            True if notification sent successfully
        """
        message = (
            "⚠️ <b>Bridge Session Alert</b>\n\n"
            f"Session: <code>{session.session_id[:16]}...</code>\n\n"
            f"Your bridge session appears to be stuck:\n"
            f"{reason}\n\n"
            f"<b>Recommended Actions:</b>\n"
            f"• Use /status to get detailed diagnostics\n"
            f"• Check transaction on blockchain explorer\n"
            f"• Contact support if issue persists\n\n"
            f"Session ID: <code>{session.session_id}</code>"
        )

        return await self._send_notification(user_id, message)

    async def _send_notification(
        self,
        user_id: int,
        message: str,
        retry: int = 3,
    ) -> bool:
        """
        Send notification to user with retry logic.

        Args:
            user_id: Telegram user ID
            message: Message text (HTML formatted)
            retry: Number of retry attempts

        Returns:
            True if sent successfully
        """
        for attempt in range(retry):
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML",
                )
                return True

            except TelegramForbiddenError:
                logger.warning("User %d blocked the bot", user_id)
                return False

            except TelegramNotFound:
                logger.warning("User %d not found", user_id)
                return False

            except Exception as e:
                logger.error(
                    "Failed to send notification to %d (attempt %d/%d): %s",
                    user_id,
                    attempt + 1,
                    retry,
                    e,
                )

                if attempt < retry - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False

        return False

    @staticmethod
    def _generate_progress_bar(percent: float, length: int = 10) -> str:
        """
        Generate visual progress bar.

        Args:
            percent: Progress percentage (0-100)
            length: Bar length in characters

        Returns:
            Progress bar string
        """
        filled = int(length * percent / 100)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percent:.0f}%"


__all__ = ["NotificationService"]

