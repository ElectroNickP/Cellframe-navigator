from __future__ import annotations

import asyncio
import logging
import os

from bot.config import get_bot_config
from watcher.chains.bsc import BSCWatcher
from watcher.chains.cf20 import CF20Watcher
from watcher.chains.eth import EthereumWatcher
from watcher.schedulers.base import PollingScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_scheduler() -> PollingScheduler:
    """Build polling scheduler with configured watchers."""
    config = get_bot_config()
    logger.info("Redis queue configured at %s", config.redis_url)

    # Ethereum configuration
    eth_rpc = os.getenv("ETH_RPC_URL", "https://mainnet.infura.io/v3/demo")
    etherscan_api = os.getenv("ETHERSCAN_API_KEY", "demo")
    eth_poll_interval = int(os.getenv("ETH_POLL_INTERVAL", "60"))
    eth_confirmations = int(os.getenv("ETH_CONFIRMATIONS_REQUIRED", "12"))
    cell_erc20 = os.getenv("CELL_ERC20_CONTRACT", "0x26c8afbbfe1ebaca03c2bb082e69d0476bffe099")

    # BSC configuration
    bsc_rpc = os.getenv("BSC_RPC_URL", "https://bsc-dataseed1.ninicoin.io")
    bscscan_api = os.getenv("BSCSCAN_API_KEY", "demo")
    bsc_poll_interval = int(os.getenv("BSC_POLL_INTERVAL", "60"))
    bsc_confirmations = int(os.getenv("BSC_CONFIRMATIONS_REQUIRED", "15"))
    cell_bep20 = os.getenv("CELL_BEP20_CONTRACT", "0x26c8afbbfe1ebaca03c2bb082e69d0476bffe099")

    # CF-20 configuration
    cf_rpc = os.getenv("CF_RPC_URL", "http://cellframe-node:8079")
    cf_network = os.getenv("CF_NETWORK", "backbone")
    cf_poll_interval = int(os.getenv("CF_POLL_INTERVAL", "120"))
    cf_confirmations = int(os.getenv("CF_CONFIRMATIONS_REQUIRED", "5"))

    logger.info("Initializing watchers...")
    logger.info("  - Ethereum: %s (confirmations: %d, interval: %ds)", 
                eth_rpc, eth_confirmations, eth_poll_interval)
    logger.info("  - BSC: %s (confirmations: %d, interval: %ds)", 
                bsc_rpc, bsc_confirmations, bsc_poll_interval)
    logger.info("  - CF-20: %s network=%s (confirmations: %d, interval: %ds)", 
                cf_rpc, cf_network, cf_confirmations, cf_poll_interval)

    watchers = [
        EthereumWatcher(
            rpc_url=eth_rpc,
            etherscan_api_key=etherscan_api,
            poll_interval=eth_poll_interval,
            confirmations_required=eth_confirmations,
            cell_contract_address=cell_erc20,
        ),
        BSCWatcher(
            rpc_url=bsc_rpc,
            bscscan_api_key=bscscan_api,
            poll_interval=bsc_poll_interval,
            confirmations_required=bsc_confirmations,
            cell_contract_address=cell_bep20,
        ),
        CF20Watcher(
            rpc_url=cf_rpc,
            network=cf_network,
            poll_interval=cf_poll_interval,
            confirmations_required=cf_confirmations,
        ),
    ]
    
    return PollingScheduler(watchers)


async def main() -> None:
    """Main entry point for watcher service."""
    logger.info("Starting Cellframe Bridge Watcher...")
    
    try:
        scheduler = build_scheduler()
        await scheduler.run()
    except Exception as e:
        logger.error("Fatal error in watcher: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Watcher stopped gracefully")
