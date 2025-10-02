from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


DIRECTIONS = {
    "eth_to_cf": "Ethereum → Cellframe",
    "bsc_to_cf": "BSC → Cellframe",
    "cf_to_eth": "Cellframe → Ethereum",
    "cf_to_bsc": "Cellframe → BSC",
}

TOKENS = {
    "eth_to_cf": ["CELL", "USDT", "USDC"],
    "bsc_to_cf": ["CELL", "BUSD", "USDT"],
    "cf_to_eth": ["CELL", "KEL"],
    "cf_to_bsc": ["CELL", "KEL"],
}


def direction_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for bridge direction selection."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"dir:{direction}")]
        for direction, label in DIRECTIONS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def token_keyboard(direction: str) -> InlineKeyboardMarkup:
    """Create keyboard for token selection based on direction."""
    tokens = TOKENS.get(direction, [])
    buttons = [
        [InlineKeyboardButton(text=token, callback_data=f"token:{token}")] 
        for token in tokens
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard for bridge session."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="confirm:no"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def action_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """Create keyboard with actions for bridge session."""
    buttons = [
        [InlineKeyboardButton(
            text="📊 Check Status",
            callback_data=f"status:{session_id}"
        )],
        [InlineKeyboardButton(
            text="🌐 Open Bridge",
            url="https://bridge.cellframe.net"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chain_name(direction_part: str) -> str:
    """Get full chain name from direction part."""
    names = {
        "eth": "Ethereum",
        "bsc": "BSC",
        "cf": "Cellframe CF-20",
    }
    return names.get(direction_part, direction_part.upper())


def parse_direction(direction: str) -> tuple[str, str]:
    """
    Parse direction string into source and destination chains.
    
    Args:
        direction: Direction string like 'eth_to_cf'
        
    Returns:
        Tuple of (source_chain, dest_chain)
    """
    parts = direction.split("_to_")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", ""


__all__ = [
    "direction_keyboard",
    "token_keyboard",
    "confirmation_keyboard",
    "action_keyboard",
    "get_chain_name",
    "parse_direction",
    "DIRECTIONS",
    "TOKENS",
]
