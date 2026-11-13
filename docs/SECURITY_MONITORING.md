# DataLens – Security Monitoring & Incident Tracking

## 1. Overview
The Security Monitoring platform continuously inspects analytical workflows and authentication boundaries to detect anomalous behavior, repeated authorization failures, and potential security breaches.

---

## 2. Tracked Incident Types & Severities
| Event Type | Trigger Criteria | Severity |
| :--- | :--- | :--- |
| `FAILED_LOGIN_BURST` | 5+ failed authentication attempts within 5 minutes | `HIGH` |
| `UNAUTHORIZED_ACCESS_BURST` | Repeated authorization failures across endpoints | `HIGH` |
| `SUSPICIOUS_AUTH` | Logins from new geolocations or anomalous IP ranges | `MEDIUM` |
| `REVOKED_TOKEN_ACCESS` | Requests utilizing revoked share tokens or sessions | `MEDIUM` |
| `POLICY_VIOLATION` | Attempts to bypass workspace export or sharing limits | `LOW` |
| `ANOMALOUS_EXPORT` | High-frequency or high-volume dataset exfiltration attempts | `CRITICAL` |

---

## 3. Investigation & Status Workflow
- Incidents default to `OPEN`.
- Administrators can advance status to `INVESTIGATING`, `RESOLVED`, or mark as `FALSE_POSITIVE`.
- Resolution notes and the resolving administrator's ID are permanently captured for compliance audits.

---

## 4. API Endpoints
- `GET /api/v1/security-events`: Query security events with status and severity filters.
- `PATCH /api/v1/security-events/{event_id}`: Update incident status and append resolution notes.

