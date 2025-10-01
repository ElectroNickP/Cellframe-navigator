from __future__ import annotations

import asyncio
from typing import Iterable, List

from web3 import Web3
from web3.middleware import geth_poa_middleware

from watcher.chains.base import BaseChainWatcher


class BSCWatcher(BaseChainWatcher):
    name = "bsc"

    def __init__(self, rpc_url: str, bscscan_api_key: str, poll_interval: int = 30) -> None:
        super().__init__(poll_interval=poll_interval)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.api_key = bscscan_api_key

    async def poll_new_transactions(self) -> Iterable[dict]:
        latest_block = await asyncio.to_thread(self.web3.eth.block_number)
        return [
            {
                "chain": self.name,
                "type": "block",
                "block_number": latest_block,
            }
        ]

    async def poll_mempool(self) -> Iterable[dict]:
        pending = await asyncio.to_thread(self.web3.eth.get_block, "pending", True)
        txs: List[dict] = []
        for tx in pending.get("transactions", [])[:5]:
            txs.append(
                {
                    "chain": self.name,
                    "type": "pending",
                    "hash": tx["hash"].hex() if hasattr(tx["hash"], "hex") else tx["hash"],
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                }
            )
        return txs


__all__ = ["BSCWatcher"]
