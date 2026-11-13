# DataLens — Report Email Delivery System

## Overview

The Report Email Delivery System automates document distribution to executives, department leads, and external stakeholders directly upon report execution.

---

## 1. Delivery Architecture

```
  [Completed ReportRun] ───► [Email Delivery Adapter]
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        [Production SMTP Adapter]              [Dev File/Log Adapter]
        - TLS / SSL Authentication             - Local file delivery dump
        - Multipart MIME construction          - Terminal / log auditing
        - Attachment size validation (25MB)    - Zero external dependency
```

---

## 2. Validation & Security Controls

### Recipient Validation
- Addresses are sanitized and validated against RFC 5322 regex:
  `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- Disallowed domains, internal blacklist restrictions, and syntax anomalies are rejected at configuration time.

### Attachment Size Enforcements
- Standard enterprise mail gateways restrict attachments above 25MB.
- The delivery engine inspects generated artifacts before transmission:
  - If payload $\le$ 25 MB: Attached directly to the outgoing email.
  - If payload $>$ 25 MB: The file is retained in DataLens storage, and an authenticated, time-limited direct download link is inserted into the email body instead.

### Template & Branding
Emails are styled using DataLens brand standards:
- Header banner with DataLens navy styling.
- Executive summary preview in the email body.
- Key KPI snapshot table.
- Link to interactive live view in DataLens.
- Attached report in user's requested format (`.pdf`, `.docx`, `.xlsx`, or `.csv`).

