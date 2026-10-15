import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from worker import handle_event


@pytest.mark.asyncio
@pytest.mark.parametrize("processing_error", [None, RuntimeError("processing failed")])
async def test_handle_event_acknowledges_processed_and_failed_messages(
    processing_error: Exception | None,
) -> None:
    engine = AsyncMock()
    session_local = MagicMock()
    record = {
        "messageId": "message-1",
        "receiptHandle": "receipt-1",
        "body": '{"job_id": "00000000-0000-0000-0000-000000000001"}',
    }

    with (
        patch("worker.create_db", return_value=(engine, session_local)),
        patch("worker.process_job", new_callable=AsyncMock) as process_job,
        patch("worker.delete_message") as delete_message,
    ):
        if processing_error is not None:
            process_job.side_effect = processing_error

        result = await handle_event({"Records": [record]})

    process_job.assert_awaited_once()
    delete_message.assert_called_once_with("receipt-1")
    assert result == {"batchItemFailures": []}
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_handle_event_retries_when_message_acknowledgment_fails() -> None:
    engine = AsyncMock()
    session_local = MagicMock()
    record = {
        "messageId": "message-1",
        "receiptHandle": "receipt-1",
        "body": '{"job_id": "00000000-0000-0000-0000-000000000001"}',
    }

    with (
        patch("worker.create_db", return_value=(engine, session_local)),
        patch("worker.process_job", new_callable=AsyncMock),
        patch("worker.delete_message", side_effect=RuntimeError("SQS down")),
    ):
        result = await handle_event({"Records": [record]})

    assert result == {
        "batchItemFailures": [{"itemIdentifier": "message-1"}]
    }
    engine.dispose.assert_awaited_once_with()
