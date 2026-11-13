# S3-Compatible Object Storage Configuration Guide

## Overview

DataLens features a universal S3 connector compatible with **Amazon Web Services (AWS) S3**, **MinIO**, **Cloudflare R2**, **Wasabi**, and **Ceph Object Gateway**. It streams both delimited CSV/TSV files and native Parquet files directly into DataLens immutable datasets.

---

## 1. AWS S3 Configuration

### Minimum IAM Policy (Least Privilege)
To ensure security, create an IAM user or role with read-only access limited strictly to the target analytics bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBucketListing",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::my-analytics-bucket"
    },
    {
      "Sid": "AllowObjectRead",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-analytics-bucket/*"
    }
  ]
}
```

### Connection Parameters
- **S3 Bucket**: `my-analytics-bucket`
- **Region**: e.g. `us-east-1` or `eu-central-1`
- **Access Key ID**: `AKIA...`
- **Secret Access Key**: `••••••••`
- **Endpoint URL**: Leave empty for standard AWS S3.

---

## 2. MinIO (On-Premises / Docker)

MinIO provides an on-premises, high-performance S3-compatible object storage service.

### Connection Parameters
- **S3 Bucket**: `warehouse`
- **Region**: `us-east-1` (default in MinIO)
- **Endpoint URL**: `http://minio.internal.company.com:9000` or `https://minio.company.com`
- **Access Key ID**: MinIO Access Key
- **Secret Access Key**: MinIO Secret Key

---

## 3. Cloudflare R2

Cloudflare R2 provides S3-compatible storage with zero egress fees.

### Locating Your R2 Endpoint
In the Cloudflare Dashboard, navigate to **R2** > **Overview** > **Account ID**.
Your S3 API endpoint URL has the format:
```
https://<ACCOUNT_ID>.r2.cloudflarestorage.com
```

### Connection Parameters
- **S3 Bucket**: Your R2 bucket name
- **Region**: `auto` (or `us-east-1`)
- **Endpoint URL**: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- **Access Key ID**: R2 Token Access Key ID
- **Secret Access Key**: R2 Token Secret Access Key

---

## 4. Supported Formats & Performance

| File Format | Streaming Method | Memory Overhead | Performance |
| :--- | :--- | :--- | :--- |
| **Parquet (`.parquet`)** | PyArrow Row Groups | Minimal (~1 row group) | Instantaneous (~100MB/s) |
| **CSV (`.csv`, `.tsv`)** | Chunked Stream | Minimal (5,000 rows/chunk) | High (~30MB/s) |

When previewing S3 files, DataLens utilizes HTTP Range Byte requests (`Range: bytes=0-1048576`) to fetch only the first 1 MB of headers and sample records without downloading multi-gigabyte files.

