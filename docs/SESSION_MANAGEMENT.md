# DataLens – Active Session Management & Token Revocation

## 1. Overview
Session Management provides users and administrators with full visibility over active client sessions, device metadata, and instant revocation capabilities to safeguard against compromised devices.

---

## 2. Session Tracking Architecture
- When an authentication token is issued, a `user_sessions` entry is generated.
- The session captures:
  - `user_id`
  - `session_token_hash` (SHA-256 of access/refresh token)
  - `ip_address`
  - `user_agent` & inferred `device_label` (e.g., "macOS Browser", "Windows Browser", "Mobile Device")
  - `last_activity_at`
  - `expires_at`
  - `is_revoked`

---

## 3. Revocation Controls
- **Individual Session Revocation**: Terminate a specific session (e.g. lost phone or old laptop).
- **Revoke All Other Sessions**: Terminates all active sessions except the currently authenticated device.
- **Backend Enforcement**: When `is_revoked = True`, subsequent requests return `HTTP 401 Unauthorized` and trigger a `REVOKED_TOKEN_ACCESS` security monitoring event.

---

## 4. API Endpoints
- `GET /api/v1/sessions`: List active sessions with current device indicators.
- `DELETE /api/v1/sessions/{session_id}`: Revoke a specific session.
- `POST /api/v1/sessions/revoke-others`: Revoke all sessions except current.

