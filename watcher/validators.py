"""
Address validation utilities for different blockchain networks.
"""
from __future__ import annotations

import re
from typing import Literal

from eth_utils import is_address as is_eth_address


ChainType = Literal["ethereum", "bsc", "cf20"]


def validate_eth_address(address: str) -> bool:
    """
    Validate Ethereum/BSC address.

    Args:
        address: Address string to validate

    Returns:
        True if valid EVM address
    """
    if not address or not isinstance(address, str):
        return False

    try:
        return is_eth_address(address)
    except Exception:
        return False


def validate_cf20_address(address: str) -> bool:
    """
    Validate CF-20 address format.

    Args:
        address: Address string to validate

    Returns:
        True if valid CF-20 address
    """
    if not address or not isinstance(address, str):
        return False

    # CF-20 address validation rules (adjust based on actual format)
    # Typically CF-20 addresses have specific format
    # For now, basic validation
    if len(address) < 20 or len(address) > 100:
        return False

    # Check for valid characters (alphanumeric + some special chars)
    if not re.match(r'^[A-Za-z0-9_-]+$', address):
        return False

    return True


def validate_address(address: str, chain: ChainType) -> bool:
    """
    Validate address for specific blockchain.

    Args:
        address: Address string to validate
        chain: Blockchain type (ethereum, bsc, cf20)

    Returns:
        True if address is valid for the chain
    """
    if chain in ("ethereum", "bsc"):
        return validate_eth_address(address)
    elif chain == "cf20":
        return validate_cf20_address(address)
    else:
        return False


def normalize_eth_address(address: str) -> str:
    """
    Normalize Ethereum/BSC address to checksum format.

    Args:
        address: Ethereum address

    Returns:
        Checksummed address
    """
    from web3 import Web3
    
    try:
        return Web3.to_checksum_address(address)
    except Exception:
        return address


__all__ = [
    "validate_eth_address",
    "validate_cf20_address",
    "validate_address",
    "normalize_eth_address",
    "ChainType",
]



