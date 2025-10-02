"""
Smart transaction diagnostics service.
Analyzes transaction status and provides actionable suggestions.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from watcher.cf20_rpc import CF20RPCClient
from watcher.evm_tracker import EVMTransactionTracker


logger = logging.getLogger(__name__)


class TransactionDiagnostics:
    """Smart diagnostics for bridge transactions."""

    def __init__(
        self,
        eth_tracker: Optional[EVMTransactionTracker] = None,
        bsc_tracker: Optional[EVMTransactionTracker] = None,
        cf_rpc_client: Optional[CF20RPCClient] = None,
    ):
        """
        Initialize diagnostics service.

        Args:
            eth_tracker: Ethereum transaction tracker
            bsc_tracker: BSC transaction tracker
            cf_rpc_client: CF-20 RPC client
        """
        self.eth_tracker = eth_tracker
        self.bsc_tracker = bsc_tracker
        self.cf_rpc_client = cf_rpc_client

    async def diagnose_transaction(
        self,
        tx_hash: str,
        chain: str,
    ) -> Dict[str, any]:
        """
        Perform comprehensive transaction diagnostics.

        Args:
            tx_hash: Transaction hash
            chain: Chain name (ethereum, bsc, cf20)

        Returns:
            Diagnostic result with status and suggestions
        """
        result = {
            "tx_hash": tx_hash,
            "chain": chain,
            "exists": False,
            "status": "unknown",
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        try:
            if chain in ("ethereum", "eth"):
                if not self.eth_tracker:
                    result["issues"].append("Ethereum tracker not available")
                    return result
                return await self._diagnose_evm_transaction(
                    tx_hash, "Ethereum", self.eth_tracker
                )

            elif chain in ("bsc", "bnb"):
                if not self.bsc_tracker:
                    result["issues"].append("BSC tracker not available")
                    return result
                return await self._diagnose_evm_transaction(
                    tx_hash, "BSC", self.bsc_tracker
                )

            elif chain in ("cf20", "cf", "cellframe"):
                if not self.cf_rpc_client:
                    result["issues"].append("CF-20 RPC client not available")
                    return result
                return await self._diagnose_cf20_transaction(tx_hash)

            else:
                result["issues"].append(f"Unknown chain: {chain}")
                result["suggestions"].append(
                    "Supported chains: ethereum, bsc, cf20"
                )

        except Exception as e:
            logger.error("Diagnostic error for %s on %s: %s", tx_hash, chain, e)
            result["issues"].append(f"Diagnostic error: {str(e)}")

        return result

    async def _diagnose_evm_transaction(
        self,
        tx_hash: str,
        chain_name: str,
        tracker: EVMTransactionTracker,
    ) -> Dict[str, any]:
        """Diagnose EVM transaction."""
        result = {
            "tx_hash": tx_hash,
            "chain": chain_name,
            "exists": False,
            "status": "unknown",
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        # Get transaction status
        status = await tracker.get_transaction_status(tx_hash)
        result["details"] = status

        if not status["exists"]:
            result["status"] = "not_found"
            result["issues"].append("Transaction not found on blockchain")
            result["suggestions"].extend([
                "• Check if transaction hash is correct",
                "• Verify you're using the right network (mainnet/testnet)",
                "• Transaction might not be broadcast yet",
                f"• Check {chain_name} explorer manually",
            ])
            return result

        result["exists"] = True

        if status["pending"]:
            result["status"] = "pending"
            result["issues"].append("Transaction is still in mempool")
            result["suggestions"].extend([
                "• Transaction is waiting to be mined",
                "• Current confirmations: 0",
                "• Check gas price - might be too low",
                "• Wait for block inclusion (usually 15-30 seconds)",
            ])
            return result

        # Transaction is mined
        confirmations = status["confirmations"]
        required = tracker.confirmations_required

        result["details"]["confirmations"] = confirmations
        result["details"]["required"] = required

        if not status["success"]:
            result["status"] = "failed"
            result["issues"].append("Transaction failed (reverted)")
            result["suggestions"].extend([
                "• Transaction was mined but execution failed",
                "• Check if you have sufficient balance",
                "• Verify contract approvals are set correctly",
                "• Gas limit might have been too low",
                "• Check bridge contract for specific error",
            ])
            return result

        if confirmations < required:
            result["status"] = "confirming"
            progress = (confirmations / required) * 100
            result["details"]["progress_percent"] = round(progress, 1)
            result["suggestions"].extend([
                f"• Confirmations: {confirmations}/{required}",
                f"• Progress: {progress:.1f}%",
                f"• Estimated wait: ~{(required - confirmations) * 12} seconds",
                "• Transaction is being confirmed, please wait",
            ])
            return result

        # Fully confirmed
        result["status"] = "confirmed"
        result["suggestions"].extend([
            f"✅ Transaction confirmed with {confirmations} confirmations",
            "• Source chain transaction complete",
            "• Check destination chain for bridged tokens",
            "• Bridge processing typically takes 1-5 minutes",
        ])

        return result

    async def _diagnose_cf20_transaction(
        self,
        tx_hash: str,
    ) -> Dict[str, any]:
        """Diagnose CF-20 transaction."""
        result = {
            "tx_hash": tx_hash,
            "chain": "CF-20",
            "exists": False,
            "status": "unknown",
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        # Check if in mempool
        in_mempool = await self.cf_rpc_client.mempool_check(tx_hash)

        if in_mempool:
            result["exists"] = True
            result["status"] = "pending"
            result["issues"].append("Transaction in mempool")
            result["suggestions"].extend([
                "• Transaction is waiting to be included in block",
                "• CF-20 block time: ~10 seconds",
                "• Wait for block inclusion",
            ])
            return result

        # Check transaction history
        txs = await self.cf_rpc_client.tx_history(tx_hash=tx_hash)

        if not txs:
            result["status"] = "not_found"
            result["issues"].append("Transaction not found")
            result["suggestions"].extend([
                "• Check if transaction hash is correct",
                "• Verify network (backbone/kelvpn)",
                "• Transaction might not be broadcast yet",
                "• Check CFSCAN manually: https://scan.cellframe.net",
            ])
            return result

        result["exists"] = True
        tx = txs[0]
        tx_status = tx.get("status", "unknown")
        result["details"] = tx

        if tx_status in ("accepted", "confirmed"):
            result["status"] = "confirmed"
            result["suggestions"].extend([
                "✅ CF-20 transaction confirmed",
                "• Transaction successfully processed",
                "• If bridging, check destination chain",
            ])

        elif tx_status in ("declined", "error", "failed"):
            result["status"] = "failed"
            result["issues"].append(f"Transaction {tx_status}")
            result["suggestions"].extend([
                "• Transaction was rejected or failed",
                "• Check if you have sufficient CELL balance for fees",
                "• Verify token balance",
                "• Check transaction details on CFSCAN",
            ])

        else:
            result["status"] = "processing"
            result["suggestions"].extend([
                f"• Status: {tx_status}",
                "• Transaction is being processed",
                "• Wait for confirmation",
            ])

        return result

    async def diagnose_bridge_session(
        self,
        src_tx_hash: Optional[str],
        dst_tx_hash: Optional[str],
        src_chain: str,
        dst_chain: str,
    ) -> Dict[str, any]:
        """
        Diagnose complete bridge session (both sides).

        Args:
            src_tx_hash: Source chain transaction hash
            dst_tx_hash: Destination chain transaction hash
            src_chain: Source chain name
            dst_chain: Destination chain name

        Returns:
            Complete bridge session diagnostics
        """
        result = {
            "source": None,
            "destination": None,
            "bridge_status": "unknown",
            "overall_issues": [],
            "next_steps": [],
        }

        # Diagnose source chain
        if src_tx_hash:
            result["source"] = await self.diagnose_transaction(src_tx_hash, src_chain)

        # Diagnose destination chain
        if dst_tx_hash:
            result["destination"] = await self.diagnose_transaction(
                dst_tx_hash, dst_chain
            )

        # Determine overall bridge status
        if result["source"]:
            src_status = result["source"]["status"]

            if src_status == "not_found":
                result["bridge_status"] = "not_started"
                result["next_steps"].extend([
                    "1. Verify source transaction was broadcast",
                    "2. Check wallet connection",
                    "3. Ensure bridge.cellframe.net is used",
                ])

            elif src_status in ("pending", "confirming"):
                result["bridge_status"] = "waiting_source"
                result["next_steps"].extend([
                    "1. Wait for source transaction to confirm",
                    "2. Bridge will process after confirmations",
                    "3. Monitor progress with /status",
                ])

            elif src_status == "failed":
                result["bridge_status"] = "failed_source"
                result["next_steps"].extend([
                    "1. Source transaction failed",
                    "2. No tokens were transferred",
                    "3. Try again with correct parameters",
                ])

            elif src_status == "confirmed":
                if not dst_tx_hash:
                    result["bridge_status"] = "processing_bridge"
                    result["next_steps"].extend([
                        "1. Source confirmed, waiting for bridge",
                        "2. Bridge processing: 1-5 minutes typical",
                        "3. Destination transaction will appear soon",
                    ])
                elif result["destination"]:
                    dst_status = result["destination"]["status"]
                    if dst_status == "confirmed":
                        result["bridge_status"] = "completed"
                        result["next_steps"].append(
                            "✅ Bridge completed successfully!"
                        )
                    elif dst_status in ("pending", "confirming"):
                        result["bridge_status"] = "finalizing"
                        result["next_steps"].extend([
                            "1. Destination transaction confirming",
                            "2. Almost done!",
                            "3. Tokens will arrive after confirmations",
                        ])

        return result

    def format_diagnostic_message(self, diagnostic: Dict[str, any]) -> str:
        """
        Format diagnostic result as user-friendly message.

        Args:
            diagnostic: Diagnostic result

        Returns:
            Formatted message
        """
        tx_hash = diagnostic.get("tx_hash", "unknown")
        chain = diagnostic.get("chain", "unknown")
        status = diagnostic.get("status", "unknown")
        exists = diagnostic.get("exists", False)

        # Status emoji
        status_emoji = {
            "not_found": "❌",
            "pending": "⏳",
            "confirming": "🔄",
            "processing": "⚙️",
            "confirmed": "✅",
            "failed": "❌",
            "unknown": "❓",
        }.get(status, "❓")

        msg = f"🔍 <b>Transaction Diagnostics</b>\n\n"
        msg += f"Hash: <code>{tx_hash[:16]}...{tx_hash[-8:]}</code>\n"
        msg += f"Chain: {chain}\n"
        msg += f"Status: {status_emoji} {status.replace('_', ' ').title()}\n\n"

        # Details
        if exists and diagnostic.get("details"):
            details = diagnostic["details"]
            if "confirmations" in details:
                conf = details["confirmations"]
                req = details.get("required", "?")
                msg += f"<b>Confirmations:</b> {conf}/{req}\n"
                if "progress_percent" in details:
                    msg += f"<b>Progress:</b> {details['progress_percent']}%\n"
            msg += "\n"

        # Issues
        if diagnostic.get("issues"):
            msg += "<b>⚠️ Issues Found:</b>\n"
            for issue in diagnostic["issues"]:
                msg += f"• {issue}\n"
            msg += "\n"

        # Suggestions
        if diagnostic.get("suggestions"):
            msg += "<b>💡 Suggestions:</b>\n"
            for suggestion in diagnostic["suggestions"]:
                msg += f"{suggestion}\n"

        return msg


__all__ = ["TransactionDiagnostics"]

