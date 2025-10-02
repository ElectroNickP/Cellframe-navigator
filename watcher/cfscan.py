"""
CFSCAN integration for public transaction verification.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class CFSCANClient:
    """Client for CFSCAN blockchain explorer API."""

    def __init__(
        self,
        api_url: str = "https://scan.cellframe.net/api",
        timeout: int = 30,
    ):
        """
        Initialize CFSCAN client.

        Args:
            api_url: CFSCAN API base URL
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    async def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """
        Get transaction details from CFSCAN.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/transaction/{tx_hash}",
                    timeout=self.timeout,
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error("CFSCAN API error for tx %s: %s", tx_hash, e)
            return None
        except Exception as e:
            logger.error("Unexpected error querying CFSCAN: %s", e)
            return None

    async def get_address_transactions(
        self,
        address: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Get transactions for address from CFSCAN.

        Args:
            address: CF-20 address
            limit: Maximum number of transactions
            offset: Pagination offset

        Returns:
            List of transactions
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/address/{address}/transactions",
                    params={"limit": limit, "offset": offset},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("transactions", [])

        except Exception as e:
            logger.error("Error getting address txs from CFSCAN: %s", e)
            return []

    async def get_block(self, block_number: int) -> Optional[Dict]:
        """
        Get block details from CFSCAN.

        Args:
            block_number: Block number

        Returns:
            Block data or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/block/{block_number}",
                    timeout=self.timeout,
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error("Error getting block from CFSCAN: %s", e)
            return None

    async def get_latest_block(self) -> Optional[int]:
        """
        Get latest block number from CFSCAN.

        Returns:
            Latest block number or None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/blocks/latest",
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("block_number")

        except Exception as e:
            logger.error("Error getting latest block from CFSCAN: %s", e)
            return None

    async def search_transactions(
        self,
        query: str,
        chain: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search transactions on CFSCAN.

        Args:
            query: Search query (hash, address, etc.)
            chain: Optional chain filter

        Returns:
            List of matching transactions
        """
        try:
            params = {"q": query}
            if chain:
                params["chain"] = chain

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/search",
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("results", [])

        except Exception as e:
            logger.error("Error searching CFSCAN: %s", e)
            return []

    def get_transaction_url(self, tx_hash: str) -> str:
        """
        Get CFSCAN URL for transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            CFSCAN transaction URL
        """
        return f"https://scan.cellframe.net/transaction/{tx_hash}"

    def get_address_url(self, address: str) -> str:
        """
        Get CFSCAN URL for address.

        Args:
            address: CF-20 address

        Returns:
            CFSCAN address URL
        """
        return f"https://scan.cellframe.net/address/{address}"

    def get_block_url(self, block_number: int) -> str:
        """
        Get CFSCAN URL for block.

        Args:
            block_number: Block number

        Returns:
            CFSCAN block URL
        """
        return f"https://scan.cellframe.net/block/{block_number}"

    async def verify_transaction_exists(self, tx_hash: str) -> bool:
        """
        Quick check if transaction exists on CFSCAN.

        Args:
            tx_hash: Transaction hash

        Returns:
            True if transaction exists
        """
        tx = await self.get_transaction(tx_hash)
        return tx is not None

    async def get_transaction_status(self, tx_hash: str) -> Optional[str]:
        """
        Get transaction status from CFSCAN.

        Args:
            tx_hash: Transaction hash

        Returns:
            Status string or None
        """
        tx = await self.get_transaction(tx_hash)
        if not tx:
            return None
        
        return tx.get("status", "unknown")


class CFSCANIntegration:
    """Integration service for CFSCAN with caching and fallback."""

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize CFSCAN integration.

        Args:
            api_url: Optional custom CFSCAN API URL
        """
        self.client = CFSCANClient(api_url) if api_url else CFSCANClient()
        self._cache: Dict[str, any] = {}

    async def get_transaction_with_cache(
        self,
        tx_hash: str,
        cache_ttl: int = 60,
    ) -> Optional[Dict]:
        """
        Get transaction with caching.

        Args:
            tx_hash: Transaction hash
            cache_ttl: Cache time-to-live in seconds

        Returns:
            Transaction data or None
        """
        # Check cache
        cache_key = f"tx:{tx_hash}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Fetch from CFSCAN
        tx = await self.client.get_transaction(tx_hash)
        
        if tx:
            self._cache[cache_key] = tx
            # Note: In production, implement proper cache expiry
        
        return tx

    def format_transaction_link(
        self,
        tx_hash: str,
        label: Optional[str] = None,
    ) -> str:
        """
        Format transaction link for Telegram message.

        Args:
            tx_hash: Transaction hash
            label: Optional link label

        Returns:
            Formatted HTML link
        """
        url = self.client.get_transaction_url(tx_hash)
        display = label or f"{tx_hash[:8]}...{tx_hash[-6:]}"
        return f'<a href="{url}">{display}</a>'

    def format_address_link(
        self,
        address: str,
        label: Optional[str] = None,
    ) -> str:
        """
        Format address link for Telegram message.

        Args:
            address: CF-20 address
            label: Optional link label

        Returns:
            Formatted HTML link
        """
        url = self.client.get_address_url(address)
        display = label or f"{address[:8]}...{address[-6:]}"
        return f'<a href="{url}">{display}</a>'


__all__ = ["CFSCANClient", "CFSCANIntegration"]

