from __future__ import annotations

import logging
from typing import Any, Dict

from redis import Redis
from rq import Queue

from bot.config import get_bot_config


logger = logging.getLogger(__name__)


def get_queue(name: str = "watcher") -> Queue:
    config = get_bot_config()
    connection = Redis.from_url(config.redis_url)
    return Queue(name, connection=connection)


def enqueue_event(event: Dict[str, Any], queue_name: str = "watcher") -> None:
    queue = get_queue(queue_name)
    logger.debug("Enqueuing event: %s", event)
    queue.enqueue("queue.tasks.process_event", event)
