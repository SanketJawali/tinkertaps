# Architecture Flow

This document contains the flow diagram for file processing.

```
                    Upload
Browser ─────────────────────────► S3
   │
   │ Process
   ▼
FastAPI
   │
   ├── Insert Job (Postgres)
   ├── Push job_id (Redis Queue)
   └── Keep SSE connection open
                │
                ▼
             Worker
                │
      Read job from Postgres
                │
      Download file from S3
                │
          Process file
                │
      Upload output to S3
                │
      Update Postgres
                │
     Publish event (Redis Pub/Sub)
                │
                ▼
             FastAPI
                │
        Send SSE to Browser
```
