# Tinkertaps Lambda Worker Setup

Short reference for the Lambda-based worker architecture: how SQS triggers Lambda, what the worker does, and how to recreate the local Floci setup.

> **Current state:** the Lambda commands are prepared. Exact Lambda networking values (`DB_HOST`, S3 endpoint, etc.) still depend on the project's `docker-compose.yml`.

---

## 1. Architecture

```text
Client
  │
  ▼
FastAPI API
  │
  ├── input ───────────────► S3
  │
  └── job ─────────────────► SQS
                              │
                              ▼
                    Lambda Event Source Mapping
                              │
                              ▼
                    Tinkertaps Lambda Worker
                              │
                     ┌────────┼────────┐
                     ▼        ▼        ▼
                    DB       S3    Processor
```

The important decision is:

**Lambda is the worker.**

There is no long-running worker process that manually polls SQS. The SQS/Lambda Event Source Mapping polls the queue and invokes the Lambda function.

---

## 2. How SQS triggers Lambda

SQS does not directly call Lambda. An **Event Source Mapping** connects them:

```text
SQS queue → Event Source Mapping → Lambda
```

Tinkertaps sends a small message:

```json
{
  "job_id": "a-real-job-uuid"
}
```

Lambda receives an event containing SQS records:

```json
{
  "Records": [
    {
      "messageId": "test-message-1",
      "body": "{\"job_id\":\"a-real-job-uuid\"}"
    }
  ]
}
```

The Lambda handler:

1. iterates over `Records`
2. parses `body`
3. extracts `job_id`
4. processes that job

The initial Event Source Mapping uses:

```text
batch size = 1
```

This keeps the first implementation simple.

---

# 3. The worker

The worker is:

```text
workers/worker.py
```

The actual processor remains separate:

```text
workers/
├── worker.py
└── scripts/
    └── image/
        └── format_convertor.py
```

The processor only transforms files:

```python
convert_image(input_path, output_path)
```

It does not know about Lambda, SQS, PostgreSQL, or S3.

The worker handles orchestration.

### Worker flow

```text
SQS event
   ↓
extract job_id
   ↓
claim job in PostgreSQL
   ↓
download input from S3
   ↓
convert image
   ↓
upload output to S3
   ↓
mark job COMPLETED
```

On failure:

```text
PROCESSING → FAILED
```

The exception is re-raised so the Lambda/SQS integration knows that the record failed.

### Atomic job claim

The worker changes:

```text
PENDING → PROCESSING
```

with a conditional database update, conceptually:

```sql
UPDATE jobs
SET status = 'PROCESSING',
    started_at = NOW()
WHERE id = :job_id
  AND status IN ('PENDING', 'FAILED')
RETURNING ...;
```

This prevents a second invocation from claiming a job that another invocation already claimed.

The worker currently allows `FAILED` jobs to be retried and increments `retry_count`.

---

# 4. Job lifecycle

The API starts the lifecycle:

```text
DRAFT → PENDING
```

The worker handles:

```text
PENDING → PROCESSING → COMPLETED
                         │
                         └→ FAILED
```

PostgreSQL remains the source of truth for job status and metadata. SQS is the mechanism used to deliver the work notification.

---

# 5. Lambda deployment package

The ZIP must have `worker.py`, `app/`, and `scripts/` at its root:

```text
tinkertaps-lambda/
├── worker.py
├── app/
├── scripts/
├── sqlalchemy/
├── asyncpg/
├── PIL/
└── ...
```

This corresponds to the Lambda handler:

```text
worker.lambda_handler
```

Build it from the repository:

```bash
mkdir -p /tmp/tinkertaps-lambda
rm -rf /tmp/tinkertaps-lambda/*

cp workers/worker.py /tmp/tinkertaps-lambda/
cp -r workers/scripts /tmp/tinkertaps-lambda/
cp -r app /tmp/tinkertaps-lambda/

uv pip install \
  --target /tmp/tinkertaps-lambda \
  boto3 sqlalchemy asyncpg pillow pydantic pydantic-settings

cd /tmp/tinkertaps-lambda
zip -r ~/tinkertaps-worker.zip .
```

`asyncpg` contains compiled components, so the package must be built for a compatible Linux environment/architecture.

---

# 6. Create the Lambda function in Floci

Set the Floci endpoint:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
```

Create the function:

```bash
aws lambda create-function \
  --function-name tinkertaps-worker \
  --runtime python3.12 \
  --role arn:aws:iam::000000000000:role/tinkertaps-lambda-role \
  --handler worker.lambda_handler \
  --zip-file fileb://$HOME/tinkertaps-worker.zip \
  --timeout 60 \
  --memory-size 512 \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

The response should identify:

```text
FunctionName: tinkertaps-worker
Runtime: python3.12
Handler: worker.lambda_handler
Timeout: 60
MemorySize: 512
```

Exact CLI formatting may differ.

---

# 7. Lambda environment

The worker needs configuration for PostgreSQL and S3:

```text
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME

AWS_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_INTERNAL_ENDPOINT_URL
S3_BUCKET_NAME
```

The Docker networking detail matters here.

Inside Lambda:

```text
localhost
```

means the Lambda container itself.

If Docker Compose contains services named `floci` and `postgres`, the values might be:

```text
AWS_INTERNAL_ENDPOINT_URL=http://floci:4566
DB_HOST=postgres
```

but **check `docker-compose.yml` before using these values**.

Configure the function once the actual service names are known:

```bash
aws lambda update-function-configuration \
  --function-name tinkertaps-worker \
  --environment 'Variables={
DB_HOST=...,
DB_PORT=...,
DB_USER=...,
DB_PASSWORD=...,
DB_NAME=...,
AWS_REGION=us-east-1,
AWS_ACCESS_KEY_ID=...,
AWS_SECRET_ACCESS_KEY=...,
AWS_INTERNAL_ENDPOINT_URL=...,
S3_BUCKET_NAME=tinkertaps-s3-file-bucket
}' \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

---

# 8. Get the SQS queue ARN

Current queue:

```bash
export SQS_QUEUE_URL=http://localhost:4566/000000000000/tinkertaps-jobs
```

Get its ARN:

```bash
aws sqs get-queue-attributes \
  --queue-url "$SQS_QUEUE_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

Expected shape:

```text
arn:aws:sqs:us-east-1:000000000000:tinkertaps-jobs
```

Save it:

```bash
export SQS_QUEUE_ARN=$(
  aws sqs get-queue-attributes \
    --queue-url "$SQS_QUEUE_URL" \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text \
    --endpoint-url "$AWS_ENDPOINT_URL"
)
```

---

# 9. SQS visibility timeout

The example Lambda timeout is:

```text
60 seconds
```

Floci's default SQS visibility timeout is:

```text
30 seconds
```

That should not be the final configuration for a worker that can run for 60 seconds.

The visibility timeout needs to be longer than the Lambda timeout. AWS recommends at least six times the Lambda timeout.

Example:

```text
Lambda timeout:         60 seconds
SQS visibility timeout: 360 seconds
```

This reduces the chance of a message becoming visible again while its Lambda invocation is still processing it.

---

# 10. Create the Event Source Mapping

```bash
aws lambda create-event-source-mapping \
  --function-name tinkertaps-worker \
  --event-source-arn "$SQS_QUEUE_ARN" \
  --batch-size 1 \
  --function-response-types ReportBatchItemFailures \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

Expected response contains information similar to:

```text
UUID: ...
State: Creating
EventSourceArn: arn:aws:sqs:...
FunctionArn: arn:aws:lambda:...
BatchSize: 1
```

Check it:

```bash
aws lambda list-event-source-mappings \
  --function-name tinkertaps-worker \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

Look for:

```text
State: Enabled
BatchSize: 1
```

---

# 11. Test Lambda directly

Before testing SQS, test Lambda itself.

Create `/tmp/lambda-event.json`:

```json
{
  "Records": [
    {
      "messageId": "test-message-1",
      "body": "{\"job_id\":\"YOUR_REAL_JOB_UUID\"}"
    }
  ]
}
```

Invoke:

```bash
aws lambda invoke \
  --function-name tinkertaps-worker \
  --payload fileb:///tmp/lambda-event.json \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-response.json \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

Check:

```bash
cat /tmp/lambda-response.json
```

Successful record handling should return:

```json
{
  "batchItemFailures": []
}
```

The job should then move:

```text
PENDING → PROCESSING → COMPLETED
```

and the output should appear in S3.

Testing Lambda directly first isolates Lambda/package/DB/S3/worker problems from SQS integration problems.

---

# 12. Test SQS → Lambda

Once direct Lambda invocation works, send a real queue message:

```bash
aws sqs send-message \
  --queue-url "$SQS_QUEUE_URL" \
  --message-body '{"job_id":"YOUR_REAL_JOB_UUID"}' \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

Expected response contains a `MessageId`.

The Event Source Mapping should then produce:

```text
SQS
 ↓
Lambda
 ↓
job_id
 ↓
PostgreSQL
 ↓
S3 input
 ↓
image converter
 ↓
S3 output
 ↓
COMPLETED
```

---

# 13. Partial batch failures

The Lambda worker returns:

```json
{
  "batchItemFailures": [
    {
      "itemIdentifier": "message-id"
    }
  ]
}
```

for records that failed.

The Event Source Mapping is configured with:

```text
ReportBatchItemFailures
```

We are initially using batch size `1`, so this is mostly preparing the worker for later batch processing.

---

# 14. Database connections

The worker uses a small SQLAlchemy pool:

```python
pool_size=1
max_overflow=0
```

This matters because Lambda can have multiple concurrent executions:

```text
Lambda #1 → DB connection
Lambda #2 → DB connection
Lambda #3 → DB connection
```

A large pool per invocation could exhaust PostgreSQL as concurrency grows.

A separate PostgreSQL role for the worker is useful for permissions, but:

```text
database role ≠ database connection
```

---

# 15. What we are deliberately leaving for later

First get the happy path working:

```text
API → SQS → Lambda → S3/DB → output
```

Then investigate:

- duplicate SQS delivery
- retry policy
- Dead Letter Queues
- stuck `PROCESSING` jobs
- visibility timeout tuning
- Lambda concurrency
- database connection limits
- idempotency
- transient vs permanent failures

The current design already introduces atomic job claiming, which is an important first protection against duplicate processing.

---

# 16. Troubleshooting order

Debug one layer at a time:

```text
1. Local processor
       ↓
2. Direct Lambda invocation
       ↓
3. SQS → Lambda
       ↓
4. Full API → SQS → Lambda flow
```

This avoids debugging the entire distributed system simultaneously.

Useful commands:

```bash
# Lambda functions
aws lambda list-functions \
  --endpoint-url "$AWS_ENDPOINT_URL"

# Inspect worker
aws lambda get-function \
  --function-name tinkertaps-worker \
  --endpoint-url "$AWS_ENDPOINT_URL"

# SQS queues
aws sqs list-queues \
  --endpoint-url "$AWS_ENDPOINT_URL"

# Event Source Mappings
aws lambda list-event-source-mappings \
  --function-name tinkertaps-worker \
  --endpoint-url "$AWS_ENDPOINT_URL"
```

---

# 17. Current status and next step

Completed conceptually:

- image processor works independently
- `workers/worker.py` is the Lambda worker
- SQS is the asynchronous job queue
- Lambda consumes SQS through an Event Source Mapping
- deployment ZIP process is defined
- Lambda creation command is defined
- Event Source Mapping command is defined
- direct Lambda test is defined

Still needed before running the final setup:

```text
docker-compose.yml
      ↓
Docker service/network names
      ↓
Lambda environment values
      ↓
Create Lambda
      ↓
Create Event Source Mapping
      ↓
Direct Lambda test
      ↓
SQS integration test
```

The next practical step is to inspect the current `docker-compose.yml` and fill in the Lambda networking values.
