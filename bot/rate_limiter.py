"""
Telegram rate limiting to prevent bot bans.

Telegram limits:
- 30 messages per second to different users
- 1 message per second to same user  
- 20 messages per minute to same group
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest


logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_per_second: float
    last_call: float = 0
    tokens: float = 0


class TelegramRateLimiter:
    """
    Rate limiter for Telegram API calls.
    
    Uses token bucket algorithm:
    - Tokens refill at constant rate
    - Each message consumes one token
    - If no tokens available, wait
    """
    
    def __init__(
        self,
        global_rate: float = 25.0,  # 25 msg/sec globally (safe margin)
        user_rate: float = 0.9,  # 0.9 msg/sec per user (1 msg/sec with margin)
    ):
        """
        Initialize rate limiter.
        
        Args:
            global_rate: Max messages per second globally
            user_rate: Max messages per second per user
        """
        self.global_limit = RateLimit(max_per_second=global_rate, tokens=global_rate)
        self.user_limits: dict[int, RateLimit] = defaultdict(
            lambda: RateLimit(max_per_second=user_rate, tokens=user_rate)
        )
        self.lock = asyncio.Lock()
        
    async def _wait_for_token(self, limit: RateLimit) -> None:
        """Wait until a token is available."""
        now = time.time()
        
        # Refill tokens based on time passed
        if limit.last_call > 0:
            time_passed = now - limit.last_call
            limit.tokens = min(
                limit.max_per_second,
                limit.tokens + (time_passed * limit.max_per_second)
            )
        
        limit.last_call = now
        
        # If no tokens available, calculate wait time
        if limit.tokens < 1.0:
            wait_time = (1.0 - limit.tokens) / limit.max_per_second
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            limit.tokens = 1.0
        
        # Consume one token
        limit.tokens -= 1.0
    
    async def acquire(self, user_id: Optional[int] = None) -> None:
        """
        Acquire permission to send message.
        
        Args:
            user_id: Optional user ID for per-user limiting
        """
        async with self.lock:
            # Global rate limit
            await self._wait_for_token(self.global_limit)
            
            # Per-user rate limit
            if user_id is not None:
                user_limit = self.user_limits[user_id]
                await self._wait_for_token(user_limit)
    
    async def send_message_safe(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        **kwargs
    ) -> Optional[any]:
        """
        Send message with rate limiting and retry logic.
        
        Args:
            bot: Bot instance
            chat_id: Chat ID
            text: Message text
            **kwargs: Additional arguments for send_message
            
        Returns:
            Message object or None if failed
        """
        await self.acquire(user_id=chat_id)
        
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except TelegramRetryAfter as e:
            logger.warning(f"Telegram rate limit hit, retry after {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            # Try again after waiting
            return await bot.send_message(chat_id, text, **kwargs)
        except TelegramBadRequest as e:
            logger.error(f"Bad request sending message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None


# Global rate limiter instance
_rate_limiter: Optional[TelegramRateLimiter] = None


def get_rate_limiter() -> TelegramRateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TelegramRateLimiter()
    return _rate_limiter

