from __future__ import annotations

import logging
from typing import Any, Dict

from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)


def process_event(event: Dict[str, Any]) -> None:
    """Process blockchain events and notify the bot."""

    logger.info("Processing event: %s", event)
    # In a real implementation you would update the database here and notify users


def enqueue_notification(user_id: int, message: str, queue_name: str = "bot") -> None:
    redis = Redis.from_url("redis://redis:6379/0")
    queue = Queue(queue_name, connection=redis)
    queue.enqueue("queue.tasks.send_message", user_id, message)


def send_message(user_id: int, message: str) -> None:
    logger.info("Would send message to %s: %s", user_id, message)
