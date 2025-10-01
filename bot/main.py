from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from bot.config import get_bot_config
from bot.handlers import register_handlers


logger = logging.getLogger(__name__)


async def set_default_commands(bot: Bot, commands: Iterable[BotCommand]) -> None:
    await bot.set_my_commands(list(commands))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = get_bot_config()
    if not config.token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    storage = RedisStorage.from_url(config.redis_url)
    bot = Bot(token=config.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)

    register_handlers(dp)

    await set_default_commands(
        bot,
        [
            BotCommand(command="bridge", description="Start a bridge session"),
            BotCommand(command="status", description="Check transaction status"),
            BotCommand(command="fees", description="See bridge fees"),
            BotCommand(command="bind", description="Bind blockchain wallets"),
            BotCommand(command="help", description="Show help"),
        ],
    )

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
