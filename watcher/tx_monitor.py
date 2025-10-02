"""
Transaction monitoring service for sending notifications.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import redis.asyncio as redis
from sqlalchemy import select
from web3 import Web3

from bot.rate_limiter import get_rate_limiter
from data.database import get_session_factory
from data.models import Transaction
from data.repositories import TransactionRepository
from watcher.evm_tracker import EVMTransactionTracker


logger = logging.getLogger(__name__)


class TransactionMonitor:
    """Monitor pending transactions and send notifications."""
    
    def __init__(self, bot_token: str, eth_rpc_url: Optional[str] = None, bsc_rpc_url: Optional[str] = None, redis_url: Optional[str] = None):
        """
        Initialize transaction monitor.
        
        Args:
            bot_token: Telegram bot token
            eth_rpc_url: Ethereum RPC URL
            bsc_rpc_url: BSC RPC URL
            redis_url: Redis URL for notification deduplication
        """
        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.session_factory = get_session_factory()
        self.rate_limiter = get_rate_limiter()
        
        # Initialize Redis for notification deduplication
        self.redis: Optional[redis.Redis] = None
        if redis_url:
            self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Initialize chain trackers
        self.trackers = {}
        if eth_rpc_url:
            web3_eth = Web3(Web3.HTTPProvider(eth_rpc_url))
            self.trackers["ethereum"] = EVMTransactionTracker(web3_eth, confirmations_required=12)
        
        if bsc_rpc_url:
            web3_bsc = Web3(Web3.HTTPProvider(bsc_rpc_url))
            self.trackers["bsc"] = EVMTransactionTracker(web3_bsc, confirmations_required=15)
        
        self._running = False
    
    async def start(self, interval: int = 30) -> None:
        """
        Start monitoring transactions.
        
        Args:
            interval: Check interval in seconds
        """
        self._running = True
        logger.info(f"Starting transaction monitor (interval: {interval}s)")
        
        while self._running:
            try:
                await self._check_pending_transactions()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in transaction monitor: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        await self.bot.session.close()
        logger.info("Transaction monitor stopped")
    
    async def _check_pending_transactions(self) -> None:
        """Check all pending transactions and update status."""
        async with self.session_factory() as session:
            tx_repo = TransactionRepository(session)
            pending_txs = await tx_repo.list_pending(limit=100)
            
            logger.debug(f"Checking {len(pending_txs)} pending transactions")
            
            for tx in pending_txs:
                await self._check_transaction(tx, tx_repo)
            
            await session.commit()
    
    async def _check_transaction(self, tx: Transaction, tx_repo: TransactionRepository) -> None:
        """
        Check single transaction and notify if confirmed.
        
        Args:
            tx: Transaction record
            tx_repo: Transaction repository
        """
        try:
            # Get tracker for chain
            tracker = self.trackers.get(tx.chain)
            if not tracker:
                logger.warning(f"No tracker for chain {tx.chain}")
                return
            
            # Get transaction status
            tx_info = await tracker.get_transaction_status(tx.hash)
            
            if not tx_info or not tx_info.get("exists"):
                logger.warning(f"Transaction {tx.hash} not found on chain {tx.chain}")
                return
            
            # Update confirmations
            confirmations = tx_info.get("confirmations", 0)
            block_number = tx_info.get("block_number")
            
            old_confirmations = tx.confirmations
            
            await tx_repo.update_status(
                tx_hash=tx.hash,
                confirmations=confirmations,
                block_number=block_number,
            )
            
            # Send notification if newly confirmed
            if confirmations >= tx.confirmations_required and old_confirmations < tx.confirmations_required:
                await self._send_confirmation_notification(tx, confirmations)
                logger.info(f"Transaction {tx.hash} confirmed! Notification sent to user.")
            
            # Send progress update for intermediate milestones
            elif confirmations > old_confirmations and confirmations in [3, 6, 9]:
                await self._send_progress_notification(tx, confirmations)
        
        except Exception as e:
            logger.error(f"Error checking transaction {tx.hash}: {e}", exc_info=True)
    
    async def _send_confirmation_notification(self, tx: Transaction, confirmations: int) -> None:
        """
        Send notification when transaction is confirmed.
        
        Args:
            tx: Transaction record
            confirmations: Number of confirmations
        """
        try:
            # Get user_id from session
            async with self.session_factory() as db_session:
                from sqlalchemy.orm import selectinload
                result = await db_session.execute(
                    select(Transaction)
                    .options(selectinload(Transaction.session))
                    .where(Transaction.id == tx.id)
                )
                tx_with_session = result.scalar_one()
                user_id = tx_with_session.session.user_id
            
            # Check Redis for deduplication
            if self.redis:
                notification_key = f"notified:{tx.hash}:{user_id}:confirmed"
                already_sent = await self.redis.get(notification_key)
                if already_sent:
                    logger.debug(f"Confirmation notification already sent for TX {tx.hash}")
                    return
            
            chain_name = "Ethereum" if tx.chain == "ethereum" else "BSC"
            
            message = (
                f"✅ <b>Transaction Confirmed!</b>\n\n"
                f"Your transaction on {chain_name} has been confirmed!\n\n"
                f"<b>TX Hash:</b> <code>{tx.hash[:10]}...{tx.hash[-8:]}</code>\n"
                f"<b>Confirmations:</b> {confirmations}/{tx.confirmations_required}\n"
                f"<b>Block:</b> {tx.block_number}\n\n"
                f"✨ Your tokens are now safe!"
            )
            
            # Send with rate limiting
            await self.rate_limiter.send_message_safe(
                self.bot,
                user_id,
                message
            )
            
            # Mark as sent in Redis (expires in 7 days)
            if self.redis:
                await self.redis.setex(notification_key, 604800, "1")
            
            logger.info(f"Sent confirmation notification for TX {tx.hash} to user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to send confirmation notification: {e}", exc_info=True)
    
    async def _send_progress_notification(self, tx: Transaction, confirmations: int) -> None:
        """
        Send progress notification for transaction.
        
        Args:
            tx: Transaction record
            confirmations: Number of confirmations
        """
        try:
            # Get user_id from session
            async with self.session_factory() as db_session:
                from sqlalchemy.orm import selectinload
                result = await db_session.execute(
                    select(Transaction)
                    .options(selectinload(Transaction.session))
                    .where(Transaction.id == tx.id)
                )
                tx_with_session = result.scalar_one()
                user_id = tx_with_session.session.user_id
            
            chain_name = "Ethereum" if tx.chain == "ethereum" else "BSC"
            progress_percent = int((confirmations / tx.confirmations_required) * 100)
            
            # Progress bar
            filled = int(progress_percent / 10)
            bar = "▰" * filled + "▱" * (10 - filled)
            
            message = (
                f"🔄 <b>Transaction Progress</b>\n\n"
                f"<b>Chain:</b> {chain_name}\n"
                f"<b>TX:</b> <code>{tx.hash[:10]}...{tx.hash[-8:]}</code>\n"
                f"<b>Status:</b> {bar} {progress_percent}%\n"
                f"<b>Confirmations:</b> {confirmations}/{tx.confirmations_required}\n\n"
                f"⏳ Almost there! {tx.confirmations_required - confirmations} more to go..."
            )
            
            # Send with rate limiting
            await self.rate_limiter.send_message_safe(
                self.bot,
                user_id,
                message
            )
            logger.info(f"Sent progress notification for TX {tx.hash} to user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to send progress notification: {e}", exc_info=True)


async def main() -> None:
    """Main entry point for transaction monitor."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    eth_rpc = os.getenv("ETH_RPC_URL")
    bsc_rpc = os.getenv("BSC_RPC_URL")
    redis_url = os.getenv("REDIS_URL")
    
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    
    monitor = TransactionMonitor(
        bot_token=bot_token,
        eth_rpc_url=eth_rpc,
        bsc_rpc_url=bsc_rpc,
        redis_url=redis_url,
    )
    
    try:
        await monitor.start(interval=30)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

