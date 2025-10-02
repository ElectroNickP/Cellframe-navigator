"""
RPC Manager with retry logic and fallback nodes.
Handles RPC failures gracefully with automatic retries and node switching.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, List, Optional
from dataclasses import dataclass
import time

from web3 import Web3
from web3.exceptions import Web3Exception


logger = logging.getLogger(__name__)


@dataclass
class RPCNode:
    """RPC node configuration."""
    url: str
    name: str
    priority: int = 0  # Lower = higher priority
    failures: int = 0
    last_failure: float = 0


class RPCManager:
    """
    Manages multiple RPC nodes with automatic failover and retry logic.
    
    Features:
    - Automatic retry with exponential backoff
    - Fallback to alternative nodes on failure
    - Node health tracking
    - Circuit breaker pattern
    """
    
    def __init__(
        self,
        nodes: List[RPCNode],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 10.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0
    ):
        """
        Initialize RPC manager.
        
        Args:
            nodes: List of RPC nodes
            max_retries: Maximum retry attempts per node
            retry_delay: Initial delay between retries (seconds)
            max_retry_delay: Maximum delay between retries
            circuit_breaker_threshold: Failures before circuit breaker opens
            circuit_breaker_timeout: Time to wait before retry after circuit break
        """
        self.nodes = sorted(nodes, key=lambda n: n.priority)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
    def _is_node_available(self, node: RPCNode) -> bool:
        """Check if node is available (circuit breaker logic)."""
        if node.failures < self.circuit_breaker_threshold:
            return True
            
        # Circuit breaker opened, check if timeout passed
        time_since_failure = time.time() - node.last_failure
        if time_since_failure > self.circuit_breaker_timeout:
            logger.info(f"Circuit breaker timeout passed for {node.name}, retrying")
            node.failures = 0  # Reset failures
            return True
            
        return False
    
    def _record_success(self, node: RPCNode):
        """Record successful RPC call."""
        node.failures = 0
        
    def _record_failure(self, node: RPCNode):
        """Record failed RPC call."""
        node.failures += 1
        node.last_failure = time.time()
        
        if node.failures >= self.circuit_breaker_threshold:
            logger.warning(
                f"Circuit breaker opened for {node.name} "
                f"({node.failures} failures)"
            )
    
    async def call_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Call function with retry logic and fallback.
        
        Args:
            func: Function to call (should accept web3 instance)
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from function call
            
        Raises:
            Exception: If all nodes fail after retries
        """
        last_exception = None
        
        for node in self.nodes:
            if not self._is_node_available(node):
                logger.debug(f"Skipping {node.name} (circuit breaker open)")
                continue
            
            logger.debug(f"Trying RPC node: {node.name}")
            
            for attempt in range(self.max_retries):
                try:
                    # Create Web3 instance for this node
                    web3 = Web3(Web3.HTTPProvider(
                        node.url,
                        request_kwargs={
                            'timeout': 30,
                            'headers': {'Cache-Control': 'no-cache'}
                        }
                    ))
                    
                    # Call the function
                    result = await asyncio.to_thread(func, web3, *args, **kwargs)
                    
                    # Success!
                    self._record_success(node)
                    logger.debug(f"RPC call succeeded on {node.name}")
                    return result
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"RPC call failed on {node.name} "
                        f"(attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    
                    if attempt < self.max_retries - 1:
                        # Calculate delay with exponential backoff
                        delay = min(
                            self.retry_delay * (2 ** attempt),
                            self.max_retry_delay
                        )
                        logger.debug(f"Retrying in {delay}s...")
                        await asyncio.sleep(delay)
            
            # All retries for this node failed
            self._record_failure(node)
            logger.error(f"All retries failed for {node.name}")
        
        # All nodes failed
        logger.error("All RPC nodes failed!")
        raise Exception(
            f"All RPC nodes failed after retries. Last error: {last_exception}"
        )


class EVMRPCManager(RPCManager):
    """Specialized RPC manager for EVM chains (Ethereum, BSC)."""
    
    def __init__(self, nodes: List[RPCNode], **kwargs):
        super().__init__(nodes, **kwargs)
        
    async def get_transaction(self, tx_hash: str) -> dict:
        """Get transaction by hash."""
        def _get_tx(web3: Web3, tx_hash: str) -> dict:
            tx = web3.eth.get_transaction(tx_hash)
            return dict(tx) if tx else None
            
        return await self.call_with_retry(_get_tx, tx_hash)
    
    async def get_transaction_receipt(self, tx_hash: str) -> dict:
        """Get transaction receipt."""
        def _get_receipt(web3: Web3, tx_hash: str) -> dict:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            return dict(receipt) if receipt else None
            
        return await self.call_with_retry(_get_receipt, tx_hash)
    
    async def get_block_number(self) -> int:
        """Get current block number."""
        def _get_block(web3: Web3) -> int:
            return web3.eth.block_number
            
        return await self.call_with_retry(_get_block)
    
    async def get_balance(self, address: str) -> int:
        """Get address balance."""
        def _get_balance(web3: Web3, address: str) -> int:
            return web3.eth.get_balance(address)
            
        return await self.call_with_retry(_get_balance, address)


# Pre-configured node sets
ETHEREUM_NODES = [
    RPCNode(
        url="https://eth.llamarpc.com",
        name="LlamaRPC ETH",
        priority=0
    ),
    RPCNode(
        url="https://rpc.ankr.com/eth",
        name="Ankr ETH",
        priority=1
    ),
    RPCNode(
        url="https://eth.public-rpc.com",
        name="Public RPC ETH",
        priority=2
    ),
]

BSC_NODES = [
    RPCNode(
        url="https://bsc-dataseed.binance.org",
        name="Binance BSC",
        priority=0
    ),
    RPCNode(
        url="https://rpc.ankr.com/bsc",
        name="Ankr BSC",
        priority=1
    ),
    RPCNode(
        url="https://bsc.public-rpc.com",
        name="Public RPC BSC",
        priority=2
    ),
]

