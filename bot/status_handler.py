"""
Enhanced /status command handler with smart diagnostics.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from aiogram import types
from web3 import Web3

from bot.storage import BindingStorage
from watcher.cf20_rpc import CF20RPCClient
from watcher.diagnostics import TransactionDiagnostics
from watcher.evm_tracker import EVMTransactionTracker


logger = logging.getLogger(__name__)


class StatusCommandHandler:
    """Handler for /status command with diagnostics."""

    def __init__(self):
        """Initialize status handler with diagnostics service."""
        # Initialize diagnostics components
        self.eth_tracker = None
        self.bsc_tracker = None
        self.cf_rpc_client = None
        self.diagnostics = None
        self.binding_storage = BindingStorage()

        self._init_diagnostics()

    def _init_diagnostics(self):
        """Initialize diagnostic services."""
        try:
            # Ethereum tracker
            eth_rpc = os.getenv("ETH_RPC_URL")
            if eth_rpc:
                eth_web3 = Web3(Web3.HTTPProvider(eth_rpc))
                eth_confirmations = int(os.getenv("ETH_CONFIRMATIONS_REQUIRED", "12"))
                self.eth_tracker = EVMTransactionTracker(
                    eth_web3, eth_confirmations
                )

            # BSC tracker
            bsc_rpc = os.getenv("BSC_RPC_URL")
            if bsc_rpc:
                bsc_web3 = Web3(Web3.HTTPProvider(bsc_rpc))
                bsc_confirmations = int(os.getenv("BSC_CONFIRMATIONS_REQUIRED", "15"))
                self.bsc_tracker = EVMTransactionTracker(
                    bsc_web3, bsc_confirmations
                )

            # CF-20 RPC client
            cf_rpc = os.getenv("CF_RPC_URL")
            cf_network = os.getenv("CF_NETWORK", "backbone")
            if cf_rpc:
                self.cf_rpc_client = CF20RPCClient(cf_rpc, cf_network)

            # Initialize diagnostics service
            self.diagnostics = TransactionDiagnostics(
                eth_tracker=self.eth_tracker,
                bsc_tracker=self.bsc_tracker,
                cf_rpc_client=self.cf_rpc_client,
            )

            logger.info("Status diagnostics initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize diagnostics: %s", e)

    async def handle_status_command(
        self,
        message: types.Message,
        tx_hash: Optional[str] = None,
    ) -> None:
        """
        Handle /status command.

        Args:
            message: Telegram message
            tx_hash: Optional transaction hash
        """
        if tx_hash:
            await self._handle_tx_status(message, tx_hash)
        else:
            await self._handle_session_list(message)

    async def _handle_tx_status(
        self,
        message: types.Message,
        tx_hash: str,
    ) -> None:
        """Handle transaction status request with diagnostics."""
        if not self.diagnostics:
            await message.answer(
                "⚠️ Diagnostics service not available.\n"
                "Please check service configuration."
            )
            return

        # Send processing message
        status_msg = await message.answer(
            "🔍 Analyzing transaction...\n"
            f"Hash: <code>{tx_hash[:16]}...{tx_hash[-8:]}</code>"
        )

        # Determine chain from tx hash format
        chain = self._detect_chain(tx_hash)

        if not chain:
            await status_msg.edit_text(
                "❌ Could not determine blockchain from transaction hash.\n\n"
                "<b>Usage:</b>\n"
                "/status &lt;tx_hash&gt; &lt;chain&gt;\n\n"
                "<b>Example:</b>\n"
                "/status 0x123... ethereum\n"
                "/status cf20_hash cf20"
            )
            return

        try:
            # Perform diagnostics
            diagnostic = await self.diagnostics.diagnose_transaction(tx_hash, chain)

            # Format and send result
            result_msg = self.diagnostics.format_diagnostic_message(diagnostic)
            await status_msg.edit_text(result_msg)

        except Exception as e:
            logger.error("Diagnostic error: %s", e)
            await status_msg.edit_text(
                f"❌ Error analyzing transaction:\n{str(e)}\n\n"
                f"Please try again or check blockchain explorer manually."
            )

    async def _handle_session_list(self, message: types.Message) -> None:
        """Handle session list request."""
        sessions = self.binding_storage.list_sessions(message.from_user.id)

        if not sessions:
            await message.answer(
                "You don't have any bridge sessions yet.\n"
                "Use /bridge to create one!"
            )
            return

        response = "📊 <b>Your Bridge Sessions:</b>\n\n"
        
        for idx, session in enumerate(sessions[-10:], 1):  # Show last 10
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄",
                "confirming": "⏳",
                "completed": "✅",
                "failed": "❌",
            }.get(session.status, "❓")

            response += (
                f"{idx}. {status_emoji} <b>{session.token}</b> {session.amount}\n"
                f"   {session.direction.replace('_to_', ' → ').upper()}\n"
                f"   Status: {session.status}\n"
                f"   ID: <code>{session.session_id[:16]}...</code>\n\n"
            )

        response += (
            "<i>Tip: Use /status &lt;tx_hash&gt; to check specific transaction</i>"
        )

        await message.answer(response)

    def _detect_chain(self, tx_hash: str) -> Optional[str]:
        """
        Detect blockchain from transaction hash format.

        Args:
            tx_hash: Transaction hash

        Returns:
            Chain name or None
        """
        # EVM chains (Ethereum, BSC) - 0x prefix, 66 chars
        if tx_hash.startswith("0x") and len(tx_hash) == 66:
            # Could be either ETH or BSC - default to ETH
            # In production, might need chain parameter or auto-check both
            return "ethereum"

        # CF-20 hashes have different format
        # Adjust based on actual CF-20 hash format
        if len(tx_hash) > 20 and not tx_hash.startswith("0x"):
            return "cf20"

        return None


__all__ = ["StatusCommandHandler"]

