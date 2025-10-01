from __future__ import annotations

import logging

from redis import Redis
from rq import Connection, Worker

from bot.config import get_bot_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    config = get_bot_config()
    redis = Redis.from_url(config.redis_url)
    with Connection(redis):
        worker = Worker(["watcher", "bot"])
        logger.info("Starting RQ worker for queues: %s", worker.queues)
        worker.work()


if __name__ == "__main__":
    main()
