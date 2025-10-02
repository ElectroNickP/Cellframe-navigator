"""
CF-20 JSON-RPC client for Cellframe node interaction.
Implements methods: TX_HISTORY, MEMPOOL, TOKEN_INFO
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class CF20RPCClient:
    """Client for interacting with Cellframe node JSON-RPC API."""

    def __init__(self, rpc_url: str, network: str = "backbone", timeout: int = 30):
        """
        Initialize CF-20 RPC client.

        Args:
            rpc_url: URL of Cellframe node RPC endpoint
            network: Network name (backbone, kelvpn)
            timeout: Request timeout in seconds
        """
        self.rpc_url = rpc_url.rstrip("/")
        self.network = network
        self.timeout = timeout

    async def _call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make JSON-RPC call to Cellframe node.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response data

        Raises:
            httpx.HTTPError: On network/HTTP errors
            ValueError: On RPC error response
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.rpc_url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown RPC error")
                    logger.error("CF-20 RPC error: %s", error_msg)
                    raise ValueError(f"RPC error: {error_msg}")

                return data.get("result", {})

        except httpx.HTTPError as e:
            logger.error("CF-20 RPC HTTP error: %s", e)
            raise

    async def tx_history(
        self,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for address or specific transaction.

        Args:
            address: CF-20 address to query
            tx_hash: Specific transaction hash
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        params = {
            "net": self.network,
        }

        if tx_hash:
            params["tx"] = tx_hash
        if address:
            params["addr"] = address
        if limit:
            params["limit"] = limit

        try:
            result = await self._call("tx_history", params)
            # Result can be dict (single tx) or list (multiple txs)
            if isinstance(result, dict):
                return [result] if result else []
            return result or []
        except Exception as e:
            logger.warning("Failed to get tx_history: %s", e)
            return []

    async def tx_all_history(
        self,
        address: str,
        chain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get complete transaction history for address across all chains.

        Args:
            address: CF-20 address to query
            chain: Optional specific chain name

        Returns:
            List of transaction dictionaries
        """
        params = {
            "net": self.network,
            "addr": address,
        }

        if chain:
            params["chain"] = chain

        try:
            result = await self._call("tx_all_history", params)
            return result or []
        except Exception as e:
            logger.warning("Failed to get tx_all_history: %s", e)
            return []

    async def mempool_list(self) -> List[Dict[str, Any]]:
        """
        Get list of transactions in mempool.

        Returns:
            List of mempool transaction dictionaries
        """
        params = {
            "net": self.network,
        }

        try:
            result = await self._call("mempool", params)
            # Handle different response formats
            if isinstance(result, dict):
                return result.get("list", [])
            return result or []
        except Exception as e:
            logger.warning("Failed to get mempool list: %s", e)
            return []

    async def mempool_check(self, tx_hash: str) -> bool:
        """
        Check if transaction is in mempool.

        Args:
            tx_hash: Transaction hash to check

        Returns:
            True if transaction is in mempool
        """
        params = {
            "net": self.network,
            "tx": tx_hash,
        }

        try:
            result = await self._call("mempool_check", params)
            # Result format may vary
            if isinstance(result, dict):
                return result.get("in_mempool", False)
            return bool(result)
        except Exception as e:
            logger.warning("Failed to check mempool: %s", e)
            return False

    async def token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a token.

        Args:
            token: Token ticker/name

        Returns:
            Token information dictionary or None
        """
        params = {
            "net": self.network,
            "token": token,
        }

        try:
            result = await self._call("token_info", params)
            return result
        except Exception as e:
            logger.warning("Failed to get token info: %s", e)
            return None

    async def token_list(self) -> List[str]:
        """
        Get list of available tokens in network.

        Returns:
            List of token tickers
        """
        params = {
            "net": self.network,
        }

        try:
            result = await self._call("token_list", params)
            if isinstance(result, list):
                return result
            # Handle dict response with tokens key
            if isinstance(result, dict):
                return result.get("tokens", [])
            return []
        except Exception as e:
            logger.warning("Failed to get token list: %s", e)
            return []

    async def tx_status(self, tx_hash: str) -> Optional[str]:
        """
        Get transaction status (pending/confirmed/error).

        Args:
            tx_hash: Transaction hash

        Returns:
            Status string or None
        """
        # First check mempool
        in_mempool = await self.mempool_check(tx_hash)
        if in_mempool:
            return "pending"

        # Check transaction history
        txs = await self.tx_history(tx_hash=tx_hash)
        if txs:
            tx = txs[0]
            # Parse status from transaction data
            # Status field may vary, adapt based on actual API
            if tx.get("status") == "accepted":
                return "confirmed"
            elif tx.get("status") == "declined":
                return "error"
            return tx.get("status", "unknown")

        return None

    async def validate_address(self, address: str) -> bool:
        """
        Validate CF-20 address format.

        Args:
            address: Address to validate

        Returns:
            True if address is valid
        """
        # CF-20 addresses typically start with specific prefix
        # Implement basic validation, enhance based on actual format
        if not address or not isinstance(address, str):
            return False

        # Basic length check (adjust based on actual CF-20 address format)
        if len(address) < 20 or len(address) > 100:
            return False

        # More sophisticated validation can be added
        # For now, accept addresses that look reasonable
        return True


__all__ = ["CF20RPCClient"]



