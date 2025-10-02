from __future__ import annotations

import logging
from typing import Iterable, List, Set

from watcher.chains.base import BaseChainWatcher
from watcher.cf20_rpc import CF20RPCClient


logger = logging.getLogger(__name__)


class CF20Watcher(BaseChainWatcher):
    """Watcher for Cellframe CF-20 blockchain."""

    name = "cf20"

    def __init__(
        self,
        rpc_url: str,
        network: str = "backbone",
        poll_interval: int = 60,
        confirmations_required: int = 5,
    ) -> None:
        """
        Initialize CF-20 watcher.

        Args:
            rpc_url: Cellframe node RPC URL
            network: Network name (backbone, kelvpn)
            poll_interval: Polling interval in seconds
            confirmations_required: Number of confirmations needed
        """
        super().__init__(poll_interval=poll_interval)
        self.rpc_client = CF20RPCClient(rpc_url, network)
        self.network = network
        self.confirmations_required = confirmations_required
        self._seen_tx_hashes: Set[str] = set()
        self._last_checked_addresses: Set[str] = set()

    async def poll_new_transactions(self) -> Iterable[dict]:
        """
        Poll for new CF-20 transactions.

        Returns:
            List of transaction events
        """
        events: List[dict] = []

        try:
            # Get general transaction history
            # In real implementation, track specific addresses from active sessions
            recent_txs = await self.rpc_client.tx_history(limit=50)

            for tx in recent_txs:
                tx_hash = tx.get("hash") or tx.get("tx_hash")
                
                if not tx_hash:
                    continue

                # Skip already seen transactions
                if tx_hash in self._seen_tx_hashes:
                    continue

                self._seen_tx_hashes.add(tx_hash)

                # Create event for processing
                event = {
                    "chain": self.name,
                    "network": self.network,
                    "type": "transaction",
                    "hash": tx_hash,
                    "status": tx.get("status", "pending"),
                    "from": tx.get("from") or tx.get("source_addr"),
                    "to": tx.get("to") or tx.get("dest_addr"),
                    "amount": tx.get("amount") or tx.get("value"),
                    "token": tx.get("token"),
                    "block": tx.get("block") or tx.get("block_number"),
                    "timestamp": tx.get("timestamp") or tx.get("ts"),
                }

                events.append(event)

            # Limit seen hashes cache size
            if len(self._seen_tx_hashes) > 10000:
                # Keep only recent half
                self._seen_tx_hashes = set(list(self._seen_tx_hashes)[-5000:])

        except Exception as e:
            logger.error("Failed to poll CF-20 transactions: %s", e)

        return events

    async def poll_mempool(self) -> Iterable[dict]:
        """
        Poll CF-20 mempool for pending transactions.

        Returns:
            List of mempool transaction events
        """
        events: List[dict] = []

        try:
            mempool_txs = await self.rpc_client.mempool_list()

            for tx in mempool_txs:
                tx_hash = tx.get("hash") or tx.get("tx_hash")
                
                if not tx_hash:
                    continue

                event = {
                    "chain": self.name,
                    "network": self.network,
                    "type": "mempool",
                    "hash": tx_hash,
                    "status": "pending",
                    "from": tx.get("from") or tx.get("source_addr"),
                    "to": tx.get("to") or tx.get("dest_addr"),
                    "amount": tx.get("amount") or tx.get("value"),
                    "token": tx.get("token"),
                    "timestamp": tx.get("timestamp") or tx.get("ts"),
                }

                events.append(event)

        except Exception as e:
            logger.error("Failed to poll CF-20 mempool: %s", e)

        return events

    async def check_transaction_status(self, tx_hash: str) -> dict:
        """
        Check status of specific CF-20 transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction status information
        """
        status = {
            "hash": tx_hash,
            "chain": self.name,
            "network": self.network,
            "exists": False,
            "pending": False,
            "confirmed": False,
            "error": None,
        }

        try:
            # Check if in mempool
            in_mempool = await self.rpc_client.mempool_check(tx_hash)
            if in_mempool:
                status["exists"] = True
                status["pending"] = True
                return status

            # Check transaction history
            txs = await self.rpc_client.tx_history(tx_hash=tx_hash)
            if txs:
                tx = txs[0]
                status["exists"] = True
                
                tx_status = tx.get("status", "unknown")
                if tx_status in ("accepted", "confirmed"):
                    status["confirmed"] = True
                elif tx_status in ("declined", "error", "failed"):
                    status["error"] = "Transaction declined or failed"
                else:
                    status["pending"] = True

        except Exception as e:
            logger.error("Failed to check CF-20 transaction status: %s", e)
            status["error"] = str(e)

        return status

    async def track_address_transactions(self, address: str) -> List[dict]:
        """
        Track all transactions for specific address.

        Args:
            address: CF-20 address to track

        Returns:
            List of transaction events
        """
        events: List[dict] = []

        try:
            txs = await self.rpc_client.tx_all_history(address)

            for tx in txs:
                tx_hash = tx.get("hash") or tx.get("tx_hash")
                
                if not tx_hash:
                    continue

                event = {
                    "chain": self.name,
                    "network": self.network,
                    "type": "address_transaction",
                    "address": address,
                    "hash": tx_hash,
                    "status": tx.get("status", "pending"),
                    "from": tx.get("from") or tx.get("source_addr"),
                    "to": tx.get("to") or tx.get("dest_addr"),
                    "amount": tx.get("amount") or tx.get("value"),
                    "token": tx.get("token"),
                    "block": tx.get("block") or tx.get("block_number"),
                    "timestamp": tx.get("timestamp") or tx.get("ts"),
                }

                events.append(event)

        except Exception as e:
            logger.error("Failed to track CF-20 address %s: %s", address, e)

        return events


__all__ = ["CF20Watcher"]
