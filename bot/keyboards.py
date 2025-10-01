from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


DIRECTIONS = {
    "eth_to_cf": "Ethereum → Cellframe",
    "bsc_to_cf": "BSC → Cellframe",
    "cf_to_eth": "Cellframe → Ethereum",
    "cf_to_bsc": "Cellframe → BSC",
}

TOKENS = {
    "eth_to_cf": ["ETH", "USDT", "USDC"],
    "bsc_to_cf": ["BNB", "BUSD", "USDT"],
    "cf_to_eth": ["CF20", "DAI"],
    "cf_to_bsc": ["CF20", "BUSD"],
}


def direction_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=direction)]
        for direction, label in DIRECTIONS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def token_keyboard(direction: str) -> InlineKeyboardMarkup:
    tokens = TOKENS.get(direction, [])
    buttons = [
        [InlineKeyboardButton(text=token, callback_data=token)] for token in tokens
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = ["direction_keyboard", "token_keyboard"]
