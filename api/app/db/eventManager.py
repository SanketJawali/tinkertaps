import asyncio
from functools import lru_cache
import asyncpg
import json

from app.core.logging import get_logger
from app.core.config import settings


logger = get_logger(__name__)


class JobEventManager:
    CHANNEL = "job_status_updates"

    def __init__(self):
        self._subscribers = {}
        self.conn: asyncpg.Connection | None = None

    async def start(self):
        self.conn = await asyncpg.connect(
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            host=settings.db_host,
            port=settings.db_port,
        )

        await self.conn.add_listener(
            self.CHANNEL,
            self._handle_notification,
        )

        logger.info(
            "Job event listener started on channel '%s'",
            self.CHANNEL,
        )

    async def stop(self):
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

        logger.info("Job event listener stopped")

    def _handle_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ):
        event = json.loads(payload)
        job_id = event["job_id"]
        # logger.info(
        #     "Received job notification: job_id=%s status=%s",
        #     job_id,
        #     event["status"],
        # )

        self.publish(job_id, event)

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """
            Subscribe to events for a specific job ID. Returns an asyncio.
            Queue that will receive status updates for the job.
        """
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[job_id] = queue
        logger.debug("Subscribed to job_id %s, total subscribers: %d",
                     job_id,
                     len(self._subscribers)
                     )
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        """
            Unsubscribe from events for a specific job ID.
            Removes the provided asyncio.Queue from the list of subscribers for the job.
        """
        self._subscribers.pop(job_id, None)

    def publish(self, job_id: str, event: dict) -> bool:
        queue = self._subscribers.get(job_id, None)
        if queue is None:
            logger.info(
                "No subscribers for job_id %s, event not published", job_id
            )
            return False

        try:
            queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Subscriber queue full for job_id=%s",
                job_id,
            )
            return False


@lru_cache()
def get_job_event_manager() -> JobEventManager:
    """
        Returns a singleton instance of JobEventManager.
    """
    return JobEventManager()
