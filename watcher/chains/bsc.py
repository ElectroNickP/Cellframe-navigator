from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Set

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware

from watcher.chains.base import BaseChainWatcher
from watcher.evm_tracker import EVMTransactionTracker


logger = logging.getLogger(__name__)


class BSCWatcher(BaseChainWatcher):
    """Watcher for Binance Smart Chain."""

    name = "bsc"

    def __init__(
        self,
        rpc_url: str,
        bscscan_api_key: str,
        poll_interval: int = 30,
        confirmations_required: int = 15,
        cell_contract_address: str = "0x26c8afbbfe1ebaca03c2bb082e69d0476bffe099",
    ) -> None:
        """
        Initialize BSC watcher.

        Args:
            rpc_url: BSC RPC endpoint URL
            bscscan_api_key: BscScan API key
            poll_interval: Polling interval in seconds
            confirmations_required: Number of confirmations needed
            cell_contract_address: CELL BEP-20 token contract address
        """
        super().__init__(poll_interval=poll_interval)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.api_key = bscscan_api_key
        self.cell_contract = cell_contract_address.lower()
        self.tracker = EVMTransactionTracker(self.web3, confirmations_required)
        self._seen_tx_hashes: Set[str] = set()
        self._last_block: int = 0

    async def poll_new_transactions(self) -> Iterable[dict]:
        """
        Poll for new BSC transactions.

        Returns:
            List of transaction events
        """
        events: List[dict] = []

        try:
            current_block = self.web3.eth.block_number
            
            if self._last_block == 0:
                # First run, only track from current block
                self._last_block = current_block
                return events

            # Process blocks since last check (limit to avoid overload)
            start_block = max(self._last_block + 1, current_block - 100)
            
            for block_num in range(start_block, current_block + 1):
                try:
                    block = await asyncio.to_thread(
                        self.web3.eth.get_block, block_num, full_transactions=True
                    )
                    
                    for tx in block.get("transactions", []):
                        tx_hash = tx["hash"].hex() if hasattr(tx["hash"], "hex") else tx["hash"]
                        
                        # Skip already seen
                        if tx_hash in self._seen_tx_hashes:
                            continue

                        # Check if transaction involves CELL token contract
                        to_addr = tx.get("to", "").lower() if tx.get("to") else ""
                        if to_addr == self.cell_contract:
                            self._seen_tx_hashes.add(tx_hash)
                            
                            event = {
                                "chain": self.name,
                                "type": "transaction",
                                "hash": tx_hash,
                                "block_number": block_num,
                                "from": tx.get("from"),
                                "to": tx.get("to"),
                                "value": str(tx.get("value", 0)),
                                "gas_price": str(tx.get("gasPrice", 0)),
                                "contract": to_addr,
                            }
                            events.append(event)

                except Exception as e:
                    logger.warning("Failed to process block %d: %s", block_num, e)
                    continue

            self._last_block = current_block

            # Limit seen hashes cache
            if len(self._seen_tx_hashes) > 10000:
                self._seen_tx_hashes = set(list(self._seen_tx_hashes)[-5000:])

        except Exception as e:
            logger.error("Failed to poll BSC transactions: %s", e)

        return events

    async def poll_mempool(self) -> Iterable[dict]:
        """
        Poll BSC mempool for pending transactions.

        Returns:
            List of pending transaction events
        """
        events: List[dict] = []

        try:
            pending = await asyncio.to_thread(self.web3.eth.get_block, "pending", True)
            
            for tx in pending.get("transactions", [])[:20]:  # Limit to avoid overload
                tx_hash = tx["hash"].hex() if hasattr(tx["hash"], "hex") else tx["hash"]
                to_addr = tx.get("to", "").lower() if tx.get("to") else ""
                
                # Only track CELL token transactions
                if to_addr == self.cell_contract:
                    event = {
                        "chain": self.name,
                        "type": "pending",
                        "hash": tx_hash,
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value": str(tx.get("value", 0)),
                        "gas_price": str(tx.get("gasPrice", 0)),
                        "contract": to_addr,
                    }
                    events.append(event)

        except Exception as e:
            logger.warning("Failed to poll BSC mempool: %s", e)

        return events

    async def check_transaction_status(self, tx_hash: str) -> dict:
        """
        Check status of specific BSC transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction status information
        """
        return await self.tracker.get_transaction_status(tx_hash)

    async def estimate_fee(self, gas_limit: int = 21000) -> dict:
        """
        Estimate current transaction fee.

        Args:
            gas_limit: Estimated gas limit

        Returns:
            Fee estimation dictionary
        """
        return await self.tracker.estimate_transaction_fee(gas_limit)


__all__ = ["BSCWatcher"]
