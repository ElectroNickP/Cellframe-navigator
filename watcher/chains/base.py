from __future__ import annotations

import abc
from typing import Iterable, List


class BaseChainWatcher(abc.ABC):
    """Base class for chain-specific watchers."""

    name: str

    def __init__(self, poll_interval: int = 30) -> None:
        self.poll_interval = poll_interval

    @abc.abstractmethod
    async def poll_new_transactions(self) -> Iterable[dict]:
        """Return an iterable with new bridge-related transactions."""

    @abc.abstractmethod
    async def poll_mempool(self) -> Iterable[dict]:
        """Return an iterable with in-flight transactions from the mempool."""

    async def collect(self) -> List[dict]:
        events: List[dict] = []
        events.extend(await self._collect_safe(self.poll_new_transactions))
        events.extend(await self._collect_safe(self.poll_mempool))
        return events

    async def _collect_safe(self, func) -> List[dict]:
        try:
            data = await func()
            return list(data)
        except Exception as exc:  # pragma: no cover - defensive logging
            # In production you would send this to Sentry/Prometheus etc.
            print(f"[{self.name}] error while polling: {exc}")
            return []
