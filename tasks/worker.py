from __future__ import annotations

import logging

from redis import Redis
from rq import Queue, Worker

from bot.config import get_bot_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    config = get_bot_config()
    redis = Redis.from_url(config.redis_url)
    
    # Create queues
    queues = [Queue(name, connection=redis) for name in ["watcher", "bot"]]
    
    # Create worker with queues
    worker = Worker(queues, connection=redis)
    logger.info("Starting RQ worker for queues: %s", [q.name for q in worker.queues])
    worker.work()


if __name__ == "__main__":
    main()
