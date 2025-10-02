"""
EVM transaction tracking utilities for Ethereum and BSC.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from web3 import Web3
from web3.types import TxReceipt


logger = logging.getLogger(__name__)


class EVMTransactionTracker:
    """Track EVM transaction confirmations and status."""

    def __init__(self, web3: Web3, confirmations_required: int = 12):
        """
        Initialize EVM transaction tracker.

        Args:
            web3: Web3 instance connected to node
            confirmations_required: Number of confirmations needed
        """
        self.web3 = web3
        self.confirmations_required = confirmations_required

    async def get_transaction_confirmations(self, tx_hash: str) -> int:
        """
        Get number of confirmations for transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Number of confirmations (0 if pending)
        """
        try:
            tx = await asyncio.to_thread(self.web3.eth.get_transaction, tx_hash)
            
            if tx.get("blockNumber") is None:
                # Transaction is still pending
                return 0

            current_block = self.web3.eth.block_number
            confirmations = max(0, current_block - tx["blockNumber"] + 1)
            
            return confirmations

        except Exception as e:
            logger.error("Failed to get confirmations for tx %s: %s", tx_hash, e)
            return 0

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[TxReceipt]:
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt or None if not found
        """
        try:
            receipt = await asyncio.to_thread(
                self.web3.eth.get_transaction_receipt, tx_hash
            )
            return receipt
        except Exception as e:
            logger.warning("Failed to get receipt for tx %s: %s", tx_hash, e)
            return None

    async def get_transaction_status(self, tx_hash: str) -> Dict[str, any]:
        """
        Get comprehensive transaction status.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dictionary with status information
        """
        status = {
            "hash": tx_hash,
            "exists": False,
            "pending": False,
            "confirmed": False,
            "success": False,
            "confirmations": 0,
            "block_number": None,
            "error": None,
        }

        try:
            # Try to get transaction
            tx = await asyncio.to_thread(self.web3.eth.get_transaction, tx_hash)
            status["exists"] = True

            if tx.get("blockNumber") is None:
                status["pending"] = True
                return status

            status["block_number"] = tx["blockNumber"]
            
            # Get confirmations
            confirmations = await self.get_transaction_confirmations(tx_hash)
            status["confirmations"] = confirmations
            status["confirmed"] = confirmations >= self.confirmations_required

            # Get receipt to check success
            receipt = await self.get_transaction_receipt(tx_hash)
            if receipt:
                status["success"] = receipt.get("status") == 1
                if not status["success"]:
                    status["error"] = "Transaction failed (reverted)"

        except Exception as e:
            logger.error("Failed to get status for tx %s: %s", tx_hash, e)
            status["error"] = str(e)

        return status

    async def wait_for_confirmations(
        self,
        tx_hash: str,
        poll_interval: int = 15,
        max_wait: int = 3600,
    ) -> bool:
        """
        Wait for transaction to reach required confirmations.

        Args:
            tx_hash: Transaction hash
            poll_interval: Seconds between checks
            max_wait: Maximum seconds to wait

        Returns:
            True if confirmed, False if timeout or error
        """
        elapsed = 0

        while elapsed < max_wait:
            confirmations = await self.get_transaction_confirmations(tx_hash)
            
            if confirmations >= self.confirmations_required:
                logger.info(
                    "Transaction %s confirmed with %d confirmations",
                    tx_hash,
                    confirmations,
                )
                return True

            logger.debug(
                "Transaction %s has %d/%d confirmations",
                tx_hash,
                confirmations,
                self.confirmations_required,
            )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning("Transaction %s confirmation timeout", tx_hash)
        return False

    async def get_gas_price(self) -> int:
        """
        Get current gas price in wei.

        Returns:
            Gas price in wei
        """
        try:
            gas_price = await asyncio.to_thread(self.web3.eth.gas_price)
            return gas_price
        except Exception as e:
            logger.error("Failed to get gas price: %s", e)
            return 0

    async def estimate_transaction_fee(
        self,
        gas_limit: int = 21000,
    ) -> Dict[str, any]:
        """
        Estimate transaction fee.

        Args:
            gas_limit: Estimated gas limit

        Returns:
            Dictionary with fee information
        """
        try:
            gas_price = await self.get_gas_price()
            fee_wei = gas_price * gas_limit
            fee_eth = self.web3.from_wei(fee_wei, "ether")

            return {
                "gas_price_gwei": self.web3.from_wei(gas_price, "gwei"),
                "gas_limit": gas_limit,
                "fee_wei": fee_wei,
                "fee_eth": float(fee_eth),
            }
        except Exception as e:
            logger.error("Failed to estimate fee: %s", e)
            return {
                "gas_price_gwei": 0,
                "gas_limit": gas_limit,
                "fee_wei": 0,
                "fee_eth": 0,
            }


__all__ = ["EVMTransactionTracker"]


