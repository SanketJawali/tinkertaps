# S3 configuration reference

Bucket: `tinkertaps-s3-file-bucket`  
IAM user (presign / backend): `tinkertaps-backend`  
Region: `ap-south-1`

Apply these in the AWS Console (or equivalent CLI). Update origins and ARNs if the bucket name, account, or deploy hosts change.

---

## Bucket CORS

**S3 → bucket → Permissions → Cross-origin resource sharing (CORS)**

Browsers upload directly to S3 with a presigned `PUT`, so the bucket must allow the web app origin and `Content-Type`.

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedOrigins": [
      "http://localhost",
      "http://localhost:4321",
      "http://127.0.0.1",
      "http://127.0.0.1:4321"
    ],
    "ExposeHeaders": ["ETag", "x-amz-request-id"],
    "MaxAgeSeconds": 3000
  }
]
```

Notes:

- Origins must match the browser origin exactly (scheme + host + port).
- Do not add `OPTIONS` to `AllowedMethods`; S3 handles preflight from this config.
- Add production origins (e.g. `https://tinkertaps.example`) before shipping.

---

## IAM identity policy (`tinkertaps-backend`)

**IAM → Users → tinkertaps-backend → Add permissions → Create inline policy (JSON)**

Presigned URLs authenticate as this user. Without `s3:PutObject` on object ARNs, browser uploads return `AccessDenied`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TinkertapsObjectAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::tinkertaps-s3-file-bucket/*"
    },
    {
      "Sid": "TinkertapsBucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "arn:aws:s3:::tinkertaps-s3-file-bucket"
    }
  ]
}
```

| Action | Why |
| --- | --- |
| `s3:PutObject` | Browser upload via presigned URL |
| `s3:GetObject` / list / multipart | API verify upload, workers, future downloads |
| `s3:DeleteObject` | Cleanup of failed/expired drafts (later) |

---

## Related API settings

The API forces a regional endpoint when generating URLs (see `api/app/services/s3.py`), e.g. `https://s3.ap-south-1.amazonaws.com`, so browser uploads do not depend on the global `s3.amazonaws.com` host.
