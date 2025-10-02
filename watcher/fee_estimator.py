"""
Fee estimation service for bridge operations.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from watcher.evm_tracker import EVMTransactionTracker


logger = logging.getLogger(__name__)


class BridgeFeeEstimator:
    """Estimate fees and times for bridge operations."""

    def __init__(
        self,
        eth_tracker: Optional[EVMTransactionTracker] = None,
        bsc_tracker: Optional[EVMTransactionTracker] = None,
    ):
        """
        Initialize fee estimator.

        Args:
            eth_tracker: Ethereum transaction tracker
            bsc_tracker: BSC transaction tracker
        """
        self.eth_tracker = eth_tracker
        self.bsc_tracker = bsc_tracker

        # Default gas limits for different operations
        self.gas_limits = {
            "eth_transfer": 21000,
            "eth_token": 65000,
            "bsc_transfer": 21000,
            "bsc_token": 55000,
        }

        # Average block times (seconds)
        self.block_times = {
            "ethereum": 12,
            "bsc": 3,
            "cf20": 10,  # Estimate, adjust based on actual CF-20 block time
        }

        # Confirmations required
        self.confirmations_required = {
            "ethereum": int(os.getenv("ETH_CONFIRMATIONS_REQUIRED", "12")),
            "bsc": int(os.getenv("BSC_CONFIRMATIONS_REQUIRED", "15")),
            "cf20": int(os.getenv("CF_CONFIRMATIONS_REQUIRED", "5")),
        }

    async def estimate_eth_fee(self, token_transfer: bool = True) -> Dict[str, any]:
        """
        Estimate Ethereum transaction fee.

        Args:
            token_transfer: True if ERC-20 token transfer

        Returns:
            Fee estimation dictionary
        """
        if not self.eth_tracker:
            logger.warning("ETH tracker not available for fee estimation")
            return self._default_fee_estimate("ethereum", token_transfer)

        gas_limit = self.gas_limits["eth_token" if token_transfer else "eth_transfer"]
        
        try:
            fee_info = await self.eth_tracker.estimate_transaction_fee(gas_limit)
            return {
                "chain": "ethereum",
                "gas_price_gwei": fee_info["gas_price_gwei"],
                "gas_limit": gas_limit,
                "estimated_fee_eth": fee_info["fee_eth"],
                "estimated_fee_usd": None,  # Would need price oracle
            }
        except Exception as e:
            logger.error("Failed to estimate ETH fee: %s", e)
            return self._default_fee_estimate("ethereum", token_transfer)

    async def estimate_bsc_fee(self, token_transfer: bool = True) -> Dict[str, any]:
        """
        Estimate BSC transaction fee.

        Args:
            token_transfer: True if BEP-20 token transfer

        Returns:
            Fee estimation dictionary
        """
        if not self.bsc_tracker:
            logger.warning("BSC tracker not available for fee estimation")
            return self._default_fee_estimate("bsc", token_transfer)

        gas_limit = self.gas_limits["bsc_token" if token_transfer else "bsc_transfer"]
        
        try:
            fee_info = await self.bsc_tracker.estimate_transaction_fee(gas_limit)
            return {
                "chain": "bsc",
                "gas_price_gwei": fee_info["gas_price_gwei"],
                "gas_limit": gas_limit,
                "estimated_fee_bnb": fee_info["fee_eth"],  # Fee in BNB
                "estimated_fee_usd": None,  # Would need price oracle
            }
        except Exception as e:
            logger.error("Failed to estimate BSC fee: %s", e)
            return self._default_fee_estimate("bsc", token_transfer)

    def estimate_cf20_fee(self) -> Dict[str, any]:
        """
        Estimate CF-20 transaction fee.

        Returns:
            Fee estimation dictionary
        """
        # CF-20 fees are typically lower and more predictable
        # This is a placeholder - adjust based on actual CF-20 fee structure
        return {
            "chain": "cf20",
            "estimated_fee_cell": "0.0001",  # Placeholder value
            "estimated_fee_usd": None,
        }

    def _default_fee_estimate(self, chain: str, token_transfer: bool) -> Dict[str, any]:
        """
        Return default fee estimate when trackers unavailable.

        Args:
            chain: Chain name
            token_transfer: Whether it's token transfer

        Returns:
            Default fee estimate
        """
        defaults = {
            "ethereum": {
                "chain": "ethereum",
                "gas_price_gwei": 50,  # Conservative estimate
                "gas_limit": 65000 if token_transfer else 21000,
                "estimated_fee_eth": 0.00325 if token_transfer else 0.00105,
            },
            "bsc": {
                "chain": "bsc",
                "gas_price_gwei": 5,
                "gas_limit": 55000 if token_transfer else 21000,
                "estimated_fee_bnb": 0.000275 if token_transfer else 0.000105,
            },
        }
        return defaults.get(chain, {})

    def estimate_bridge_time(
        self,
        src_chain: str,
        dst_chain: str,
    ) -> int:
        """
        Estimate total bridge time in seconds.

        Args:
            src_chain: Source chain name
            dst_chain: Destination chain name

        Returns:
            Estimated time in seconds
        """
        # Source chain confirmation time
        src_confirmations = self.confirmations_required.get(src_chain, 12)
        src_block_time = self.block_times.get(src_chain, 12)
        src_time = src_confirmations * src_block_time

        # Bridge processing time (estimate)
        bridge_processing = 60  # 1 minute for bridge processing

        # Destination chain confirmation time
        dst_confirmations = self.confirmations_required.get(dst_chain, 12)
        dst_block_time = self.block_times.get(dst_chain, 12)
        dst_time = dst_confirmations * dst_block_time

        total_seconds = src_time + bridge_processing + dst_time

        return total_seconds

    async def estimate_full_bridge_cost(
        self,
        direction: str,
        token: str,
        amount: float,
    ) -> Dict[str, any]:
        """
        Estimate full bridge operation cost and time.

        Args:
            direction: Bridge direction (e.g., 'eth_to_cf', 'cf_to_bsc')
            token: Token being bridged
            amount: Amount being bridged

        Returns:
            Complete estimation dictionary
        """
        parts = direction.split("_to_")
        if len(parts) != 2:
            raise ValueError(f"Invalid direction format: {direction}")

        src_chain, dst_chain = parts

        # Estimate fees for both sides
        src_fee = {}
        dst_fee = {}

        if src_chain == "eth":
            src_fee = await self.estimate_eth_fee(token_transfer=True)
        elif src_chain == "bsc":
            src_fee = await self.estimate_bsc_fee(token_transfer=True)
        elif src_chain == "cf":
            src_fee = self.estimate_cf20_fee()

        if dst_chain == "eth":
            dst_fee = await self.estimate_eth_fee(token_transfer=True)
        elif dst_chain == "bsc":
            dst_fee = await self.estimate_bsc_fee(token_transfer=True)
        elif dst_chain == "cf":
            dst_fee = self.estimate_cf20_fee()

        # Estimate time
        estimated_time = self.estimate_bridge_time(src_chain, dst_chain)

        return {
            "direction": direction,
            "token": token,
            "amount": amount,
            "src_chain": src_chain,
            "dst_chain": dst_chain,
            "src_fee": src_fee,
            "dst_fee": dst_fee,
            "estimated_time_seconds": estimated_time,
            "estimated_time_minutes": round(estimated_time / 60, 1),
        }

    def format_fee_message(self, estimation: Dict[str, any]) -> str:
        """
        Format fee estimation as user-friendly message.

        Args:
            estimation: Fee estimation dictionary

        Returns:
            Formatted message string
        """
        src_chain = estimation["src_chain"].upper()
        dst_chain = estimation["dst_chain"].upper()
        
        src_fee = estimation.get("src_fee", {})
        dst_fee = estimation.get("dst_fee", {})

        time_min = estimation["estimated_time_minutes"]

        msg = f"<b>Bridge Fee Estimation</b>\n\n"
        msg += f"Direction: {src_chain} → {dst_chain}\n"
        msg += f"Token: {estimation['token']}\n"
        msg += f"Amount: {estimation['amount']}\n\n"

        msg += f"<b>Source Chain ({src_chain}):</b>\n"
        if "estimated_fee_eth" in src_fee:
            msg += f"Fee: ~{src_fee['estimated_fee_eth']:.5f} ETH\n"
        elif "estimated_fee_bnb" in src_fee:
            msg += f"Fee: ~{src_fee['estimated_fee_bnb']:.5f} BNB\n"
        elif "estimated_fee_cell" in src_fee:
            msg += f"Fee: ~{src_fee['estimated_fee_cell']} CELL\n"

        msg += f"\n<b>Destination Chain ({dst_chain}):</b>\n"
        if "estimated_fee_eth" in dst_fee:
            msg += f"Fee: ~{dst_fee['estimated_fee_eth']:.5f} ETH\n"
        elif "estimated_fee_bnb" in dst_fee:
            msg += f"Fee: ~{dst_fee['estimated_fee_bnb']:.5f} BNB\n"
        elif "estimated_fee_cell" in dst_fee:
            msg += f"Fee: ~{dst_fee['estimated_fee_cell']} CELL\n"

        msg += f"\n<b>Estimated Time:</b> ~{time_min} minutes\n"
        msg += f"\n<i>Note: Fees may vary based on network congestion</i>"

        return msg


__all__ = ["BridgeFeeEstimator"]


