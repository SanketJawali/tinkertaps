# SQS Job Queue

Tinkertaps uses **Amazon SQS (Simple Queue Service)** as the job queue between the API and background job workers.

The API does not perform long-running processing itself. Instead, it creates a job and places a message containing the `job_id` onto the SQS queue. A background worker can then consume the message and process the job asynchronously.

## Job Message

A job message currently contains the ID of the job that should be processed:

```json
{
  "job_id": "..."
}
```

The message contains only the identifier. The worker is responsible for retrieving the job's data from the appropriate storage/database and performing the actual processing.

## Message Lifecycle

A message follows this general lifecycle:

```text
API
 │
 │ send_message()
 ▼
SQS Queue
 │
 │ receive_message()
 ▼
Worker
 │
 │ message becomes temporarily invisible
 │
 ├── processing succeeds
 │        │
 │        ▼
 │   delete_message()
 │        │
 │        ▼
 │   Message removed
 │
 └── processing fails / worker crashes
          │
          ▼
     Message is NOT deleted
          │
          ▼
     Visibility timeout expires
          │
          ▼
     Message becomes available again
```

### 1. Enqueue

The API sends a message to SQS using `send_message()`.

The message contains the `job_id`. SQS returns a `MessageId` that can be logged for tracing.

> NOTE: The `boto3` SDK is a Synchronous library, so the functions to adding job to SQS and getting a job from it are Blocking in nature. The API routes for `/job` route are defined with `async def`, to prevent blocking of this function call in the main event loop, the `send_message()` function is called using `fastapi.run_in_threadpool()` to run it in a separate thread.

### 2. Receive

A worker calls `receive_message()` (Blocking call, as `boto3` is Synchronous) to retrieve a job.

Receiving a message does **not** permanently remove it from the queue. Instead, SQS makes the message temporarily invisible to other consumers for the configured **Visibility Timeout**.

This allows multiple workers to consume jobs concurrently without normally receiving the same visible message at the same time.

### 3. Process

The worker extracts the `job_id` from the message and performs the associated job.

The worker should only acknowledge successful processing by deleting the message.

### 4. Delete / Acknowledge

After successful processing, the worker calls `delete_message()` using the message's `ReceiptHandle`.

Deleting the message tells SQS that processing completed successfully, so the message will not be delivered again.

### 5. Failed Processing

If the worker fails or crashes before deleting the message, the message remains in SQS.

After the visibility timeout expires, SQS makes the message available again for another receive attempt.

This provides automatic retry behavior without the worker having to manually re-enqueue failed jobs.

## Visibility Timeout

The visibility timeout provides a temporary lease on a received message.

It prevents the same message from being immediately visible to other workers after one worker receives it.

However, SQS does **not** provide a general guarantee that a job will only ever be processed once. If processing takes longer than the visibility timeout, or certain delivery conditions occur, the same message may be delivered more than once.

Therefore, the eventual job-processing logic should be designed to tolerate duplicate processing (**idempotency**).

## Long Polling

Workers use SQS long polling when receiving messages:

```python
WaitTimeSeconds=10
```

Instead of repeatedly making requests when the queue is empty, SQS waits for up to the configured period for a message to become available.

This reduces unnecessary polling requests and makes queue consumption more efficient.

## Current Architecture

```text
┌──────────────┐
│   FastAPI    │
│     API      │
└──────┬───────┘
       │
       │ enqueue_job(job_id)
       ▼
┌──────────────┐
│  SQS Queue   │
└──────┬───────┘
       │
       │ receive_job()
       ▼
┌──────────────────────────┐
│     Background Worker    │
│                          │
│  receive → process       │
│              → delete    │
└──────────────────────────┘
```

Multiple worker processes can consume from the same queue concurrently. SQS manages message visibility while the workers are responsible for processing and acknowledging successful jobs.

## Future Considerations

The basic queue is now in place. The worker implementation will later need to address:

* Appropriate visibility timeout for job duration.
* Handling and testing failed jobs.
* Duplicate message delivery and idempotent processing.
* Retry behavior and maximum receive attempts.
* Dead-letter queues (DLQ) for repeatedly failing jobs.
* Monitoring and observability.
* Automated tests for enqueue, receive, processing, and deletion behavior.
