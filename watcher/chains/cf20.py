from __future__ import annotations

from typing import Iterable

import httpx

from watcher.chains.base import BaseChainWatcher


class CF20Watcher(BaseChainWatcher):
    name = "cf20"

    def __init__(self, rpc_url: str, poll_interval: int = 60) -> None:
        super().__init__(poll_interval=poll_interval)
        self.rpc_url = rpc_url.rstrip("/")

    async def poll_new_transactions(self) -> Iterable[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tx_history", "params": []},
                timeout=30,
            )
            response.raise_for_status()
            history = response.json().get("result", [])
            return [
                {
                    "chain": self.name,
                    "type": "tx_history",
                    "tx": tx,
                }
                for tx in history
            ]

    async def poll_mempool(self) -> Iterable[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "mempool", "params": []},
                timeout=30,
            )
            response.raise_for_status()
            mempool = response.json().get("result", [])
            return [
                {
                    "chain": self.name,
                    "type": "mempool",
                    "tx": tx,
                }
                for tx in mempool
            ]


__all__ = ["CF20Watcher"]
