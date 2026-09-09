## Local AWS Infrastructure with Floci

During development, the project uses **Floci** as a local AWS API simulator instead of connecting directly to AWS. This allows the application to use AWS-style services locally without incurring AWS costs, while also making it easier to experiment with additional AWS services during development.

The production infrastructure is still intended to use actual AWS services.

### Current Floci Setup

Floci runs locally on:

```text
http://localhost:4566
```

The backend and frontend have been configured to use this local endpoint instead of the corresponding AWS endpoints.

#### IAM

An IAM role has been created for the backend:

```text
Role: tinkertaps-backend
```

This role is intended to represent the permissions used by the Tinkertaps backend when interacting with AWS services.

#### S3

A development S3 bucket has been created:

```text
Bucket: tinkertaps-s3-file-bucket
Endpoint: http://localhost:4566
```

The backend uses the local S3 endpoint when generating presigned URLs and interacting with the bucket.

### S3 CORS Configuration

Because the frontend uploads files directly to S3 using presigned URLs, the local S3 bucket must allow requests originating from the frontend.

The bucket is configured to allow the local frontend origins:

```text
http://localhost:4321
http://localhost:80
http://localhost
```

Allowed methods:

```text
PUT
GET
HEAD
```

All request headers are allowed, and the `ETag` response header is exposed to the frontend.

The configuration can be applied with:

```bash
aws s3api put-bucket-cors \
  --bucket tinkertaps-s3-file-bucket \
  --cors-configuration '{
    "CORSRules": [{
      "AllowedOrigins": [
        "http://localhost:4321",
        "http://localhost:80",
        "http://localhost"
      ],
      "AllowedMethods": ["PUT", "GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }]
  }' \
  --endpoint-url http://localhost:4566
```

> **Note:** The CORS configuration is required because the browser communicates directly with the S3 endpoint during file uploads. The backend generating a presigned URL does not bypass the browser's CORS restrictions.

### Why Floci?

Floci is currently used only as a **development infrastructure layer**. It provides a local environment for experimenting with AWS services without the cost of running those services in an AWS account.

The goal is to develop and test the application's infrastructure locally first, then adapt the configuration for the actual AWS environment during deployment.

**Current flow:**

```text
Frontend
   │
   │ request presigned URL
   ▼
Backend
   │
   │ local AWS API
   ▼
Floci :4566
   │
   ▼
S3: tinkertaps-s3-file-bucket
   ▲
   │
   │ presigned upload
   │
Frontend
```
