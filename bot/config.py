from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


@dataclass
class BotConfig:
    token: str
    redis_url: str
    database_url: str
    allowed_chat_ids: Optional[str] = None


def get_bot_config() -> BotConfig:
    """Load configuration values for the Telegram bot."""

    return BotConfig(
        token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@db:5432/cellframe",
        ),
        allowed_chat_ids=os.getenv("ALLOWED_CHAT_IDS"),
    )
