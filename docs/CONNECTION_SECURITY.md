# DataLens Connection Security & SSRF Protection

## 1. Threat Model & Security Posture

External connectors necessarily handle sensitive credentials (database passwords, API tokens, OAuth refresh tokens, and AWS access keys). DataLens implements defense-in-depth principles across storage, transmission, and network egress boundaries.

```
                    ┌─────────────────────────┐
                    │ Client Browser/Frontend │
                    └───────────┬─────────────┘
                                │ JSON Over TLS 1.3
                                │ (Secrets MASKED: ••••••••)
                                ▼
                    ┌─────────────────────────┐
                    │  DataLens FastAPI API   │
                    └─────┬─────────────┬─────┘
                          │             │
        AES-256-GCM       │             │ SSRF Validation &
        Encryption Vault  │             │ DNS Resolution Check
                          ▼             ▼
              ┌───────────────┐     ┌───────────────────────┐
              │  PostgreSQL   │     │  Outbound Network     │
              │  Encrypted    │     │  (Blocks RFC 1918,    │
              │  Credentials  │     │   Loopback, Metadata) │
              └───────────────┘     └───────────────────────┘
```

---

## 2. AES-256-GCM Credential Encryption

All sensitive credential dictionaries are encrypted at rest using AES-256 in Galois/Counter Mode (GCM), providing both **confidentiality** and **authenticated integrity**.

### Key Derivation
- Master encryption key derived using SHA-256 over `settings.SECRET_KEY`.
- Generates a fixed 256-bit cryptographic key.

### Encryption Lifecycle
1. Dictionary serialized to UTF-8 JSON bytes.
2. A cryptographically secure random 12-byte IV (nonce) is generated per encryption operation via `os.urandom(12)`.
3. AES-GCM generates ciphertext with a 16-byte authentication tag appended.
4. Combined binary payload: `nonce (12 bytes) + ciphertext + auth_tag (16 bytes)`.
5. Stored in PostgreSQL `data_source_connections.encrypted_credentials` as a standard Base64 string.

### Decryption Integrity
- If ciphertext or authentication tag is tampered with or corrupted, `AESGCM.decrypt()` immediately raises `ValueError("Failed to decrypt credentials")`, preventing bit-flipping attacks.

---

## 3. Zero Secret Leakage & Credential Masking

DataLens enforces an absolute zero secret leakage policy in API responses:

1. **Database Schema Separation**: The database schema `DataSourceConnection` keeps `encrypted_credentials` strictly out of the Pydantic `ConnectionResponse` schema.
2. **Recursive Masking**: The `mask_credentials(dict)` utility recursively scrubs configuration dictionaries before sending them to the client.
3. **Targeted Mask Patterns**: Any key containing `password`, `secret`, `api_key`, `token`, `refresh_token`, `client_secret`, `private_key`, `session_token`, or `uri` is sanitized to `••••••••[last4]`.
4. **Input Masking in Frontend**: UI password inputs default to masked `type="password"` with visibility toggle.

---

## 4. Server-Side Request Forgery (SSRF) Protection

When users configure REST API endpoints, malicious inputs could attempt to probe internal infrastructure, cloud metadata endpoints, or local services.

The `SSRFValidator` (`backend/app/connectors/security.py`) executes mandatory pre-flight validation on all outbound URLs:

### Enforced Rules
1. **Explicit Protocol**: URL must explicitly declare `https://` (HTTP prohibited unless `allow_http=True` is explicitly toggled by an administrator).
2. **Synchronous DNS Resolution**: The validator resolves the target hostname using `socket.getaddrinfo()` to all bound IPv4 and IPv6 addresses.
3. **Blocked IP Ranges**:

| Network Category | Subnet | Risk Mitigated |
| :--- | :--- | :--- |
| **Loopback** | `127.0.0.0/8`, `::1/128` | Localhost services (e.g. redis, postgres) |
| **Link-Local** | `169.254.0.0/16`, `fe80::/10` | AWS/GCP/Azure Instance Metadata (`169.254.169.254`) |
| **Private Class A** | `10.0.0.0/8` | Internal corporate VPC |
| **Private Class B** | `172.16.0.0/12` | Docker bridge networks, internal clusters |
| **Private Class C** | `192.168.0.0/16` | Internal office / home networks |
| **Carrier Grade NAT**| `100.64.0.0/10` | ISP-level routing |
| **Multicast / Reserved**| `224.0.0.0/4`, `240.0.0.0/4` | Broadcast storms and invalid endpoints |

If any resolved IP falls into a blocked subnet, `SSRFSecurityError` is raised immediately, terminating the connection attempt before any HTTP socket is opened.

