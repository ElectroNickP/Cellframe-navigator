from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from watcher.chains.base import BaseChainWatcher
from watcher.utils import enqueue_event


logger = logging.getLogger(__name__)


class PollingScheduler:
    """Simple polling scheduler for watcher modules."""

    def __init__(self, watchers: Iterable[BaseChainWatcher]) -> None:
        self.watchers = list(watchers)

    async def run(self) -> None:
        tasks = [asyncio.create_task(self._run_watcher(watcher)) for watcher in self.watchers]
        await asyncio.gather(*tasks)

    async def _run_watcher(self, watcher: BaseChainWatcher) -> None:
        logger.info("Starting watcher: %s", watcher.name)
        while True:
            events = await watcher.collect()
            for event in events:
                enqueue_event(event)
            await asyncio.sleep(watcher.poll_interval)
