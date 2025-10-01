from __future__ import annotations

import asyncio
import logging
import os

from bot.config import get_bot_config
from watcher.chains.bsc import BSCWatcher
from watcher.chains.cf20 import CF20Watcher
from watcher.chains.eth import EthereumWatcher
from watcher.schedulers.base import PollingScheduler


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_scheduler() -> PollingScheduler:
    config = get_bot_config()
    logger.info("Redis queue configured at %s", config.redis_url)

    eth_rpc = os.getenv("ETH_RPC_URL", "https://mainnet.infura.io/v3/demo")
    etherscan_api = os.getenv("ETHERSCAN_API_KEY", "demo")

    bsc_rpc = os.getenv("BSC_RPC_URL", "https://bsc-dataseed1.ninicoin.io")
    bscscan_api = os.getenv("BSCSCAN_API_KEY", "demo")

    cf_rpc = os.getenv("CF_RPC_URL", "http://cellframe-node:8000")

    watchers = [
        EthereumWatcher(eth_rpc, etherscan_api, poll_interval=60),
        BSCWatcher(bsc_rpc, bscscan_api, poll_interval=60),
        CF20Watcher(cf_rpc, poll_interval=120),
    ]
    return PollingScheduler(watchers)


async def main() -> None:
    scheduler = build_scheduler()
    await scheduler.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Watcher stopped")
