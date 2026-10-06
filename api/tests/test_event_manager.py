from unittest.mock import AsyncMock, patch

from app.db.eventManager import JobEventManager, get_job_event_manager


async def test_start_connects_to_postgres_and_registers_listener():
    connection = AsyncMock()

    with patch("app.db.eventManager.asyncpg.connect", new_callable=AsyncMock) as connect:
        connect.return_value = connection
        manager = JobEventManager()

        await manager.start()

    connect.assert_awaited_once()
    connection.add_listener.assert_awaited_once_with(
        "job_status_updates",
        manager._handle_notification,
    )
    assert manager.conn is connection


async def test_stop_closes_the_database_connection():
    manager = JobEventManager()
    manager.conn = AsyncMock()

    await manager.stop()

    manager.conn.close.assert_awaited_once_with()


async def test_publish_delivers_event_to_subscriber():
    manager = JobEventManager()
    queue = manager.subscribe("job-123")
    event = {"status": "completed"}

    assert manager.publish("job-123", event) is True
    assert await queue.get() == event


def test_publish_returns_false_without_subscriber():
    manager = JobEventManager()

    assert manager.publish("job-123", {"status": "completed"}) is False


def test_publish_returns_false_when_subscriber_queue_is_full():
    manager = JobEventManager()
    queue = manager.subscribe("job-123")

    for event_number in range(queue.maxsize):
        assert manager.publish("job-123", {"number": event_number}) is True

    assert manager.publish("job-123", {"number": queue.maxsize}) is False


def test_unsubscribe_removes_job_subscription():
    manager = JobEventManager()
    queue = manager.subscribe("job-123")

    manager.unsubscribe("job-123", queue)

    assert manager.publish("job-123", {"status": "completed"}) is False


def test_get_job_event_manager_returns_singleton():
    get_job_event_manager.cache_clear()

    first_manager = get_job_event_manager()
    second_manager = get_job_event_manager()

    assert first_manager is second_manager

    get_job_event_manager.cache_clear()


async def test_lifespan_starts_and_stops_event_manager():
    manager = AsyncMock()
    app_engine = AsyncMock()

    with (
        patch("app.main.JobEventManager", return_value=manager),
        patch("app.main.engine", app_engine),
    ):
        from app.main import lifespan

        async with lifespan(object()):
            pass

    manager.start.assert_awaited_once_with()
    manager.stop.assert_awaited_once_with()
    app_engine.dispose.assert_awaited_once_with()