"""
Minimal watcher configuration - only with available RPC endpoints.
Can work with just Telegram bot token if no watchers are enabled.
"""
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
    """Build polling scheduler with only available watchers."""
    config = get_bot_config()
    logger.info("Redis queue configured at %s", config.redis_url)

    watchers = []

    # Ethereum watcher (optional)
    eth_rpc = os.getenv("ETH_RPC_URL")
    if eth_rpc:
        try:
            logger.info("Configuring Ethereum watcher...")
            etherscan_api = os.getenv("ETHERSCAN_API_KEY", "")
            eth_poll_interval = int(os.getenv("ETH_POLL_INTERVAL", "60"))
            eth_confirmations = int(os.getenv("ETH_CONFIRMATIONS_REQUIRED", "12"))
            cell_erc20 = os.getenv("CELL_ERC20_CONTRACT", "0x26c8afbbfe1ebaca03c2bb082e69d0476bffe099")

            watchers.append(EthereumWatcher(
                rpc_url=eth_rpc,
                etherscan_api_key=etherscan_api,
                poll_interval=eth_poll_interval,
                confirmations_required=eth_confirmations,
                cell_contract_address=cell_erc20,
            ))
            logger.info("✅ Ethereum watcher enabled: %s", eth_rpc)
        except Exception as e:
            logger.warning("⚠️ Failed to initialize Ethereum watcher: %s", e)
    else:
        logger.info("ℹ️ Ethereum watcher disabled (ETH_RPC_URL not set)")

    # BSC watcher (optional)
    bsc_rpc = os.getenv("BSC_RPC_URL")
    if bsc_rpc:
        try:
            logger.info("Configuring BSC watcher...")
            bscscan_api = os.getenv("BSCSCAN_API_KEY", "")
            bsc_poll_interval = int(os.getenv("BSC_POLL_INTERVAL", "60"))
            bsc_confirmations = int(os.getenv("BSC_CONFIRMATIONS_REQUIRED", "15"))
            cell_bep20 = os.getenv("CELL_BEP20_CONTRACT", "0x26c8afbbfe1ebaca03c2bb082e69d0476bffe099")

            watchers.append(BSCWatcher(
                rpc_url=bsc_rpc,
                bscscan_api_key=bscscan_api,
                poll_interval=bsc_poll_interval,
                confirmations_required=bsc_confirmations,
                cell_contract_address=cell_bep20,
            ))
            logger.info("✅ BSC watcher enabled: %s", bsc_rpc)
        except Exception as e:
            logger.warning("⚠️ Failed to initialize BSC watcher: %s", e)
    else:
        logger.info("ℹ️ BSC watcher disabled (BSC_RPC_URL not set)")

    # CF-20 watcher (optional)
    cf_rpc = os.getenv("CF_RPC_URL")
    if cf_rpc:
        try:
            logger.info("Configuring CF-20 watcher...")
            cf_network = os.getenv("CF_NETWORK", "backbone")
            cf_poll_interval = int(os.getenv("CF_POLL_INTERVAL", "120"))
            cf_confirmations = int(os.getenv("CF_CONFIRMATIONS_REQUIRED", "5"))

            watchers.append(CF20Watcher(
                rpc_url=cf_rpc,
                network=cf_network,
                poll_interval=cf_poll_interval,
                confirmations_required=cf_confirmations,
            ))
            logger.info("✅ CF-20 watcher enabled: %s (network: %s)", cf_rpc, cf_network)
        except Exception as e:
            logger.warning("⚠️ Failed to initialize CF-20 watcher: %s", e)
    else:
        logger.info("ℹ️ CF-20 watcher disabled (CF_RPC_URL not set)")

    # Summary
    logger.info("=" * 50)
    if watchers:
        logger.info("✅ Initialized %d watcher(s)", len(watchers))
        for watcher in watchers:
            logger.info("   - %s", watcher.name)
    else:
        logger.warning("⚠️ No watchers configured!")
        logger.warning("Bot will work, but won't monitor blockchain transactions")
        logger.warning("Add RPC URLs to enable monitoring")
    logger.info("=" * 50)

    return PollingScheduler(watchers)


async def main() -> None:
    """Main entry point for watcher service."""
    logger.info("Starting Cellframe Bridge Watcher...")
    
    try:
        scheduler = build_scheduler()
        
        if not scheduler.watchers:
            logger.warning("No watchers enabled - running in bot-only mode")
            logger.info("Watcher service will idle (bot will still work)")
            # Keep service alive but do nothing
            while True:
                await asyncio.sleep(3600)
        else:
            await scheduler.run()
            
    except Exception as e:
        logger.error("Fatal error in watcher: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Watcher stopped gracefully")

