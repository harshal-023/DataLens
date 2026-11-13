# DataLens – Team Collaboration Security & RBAC Boundaries

## 1. Threat Model & Boundaries
Phase 5B introduces collaborative features requiring rigorous multi-tenant security boundaries to prevent unauthorized resource leakage, privilege escalation, or session hijacking across workspaces.

---

## 2. Key Security Controls

### 2.1 Workspace Isolation
- All collaboration database queries strictly enforce `workspace_id == current_workspace.id`.
- Users cannot share or duplicate resources into workspaces where they lack membership or editor privileges.

### 2.2 Token Protection
- Share link tokens and invitation tokens use 32-byte cryptographic entropy (`secrets.token_urlsafe(32)`).
- Tokens are stored exclusively as SHA-256 hashes (`token_hash = sha256(raw_token)`).
- Raw tokens are never logged or persisted to disk.

### 2.3 Password Protection
- Shared links can optionally mandate a password.
- Passwords are validated using SHA-256 hashing.
- Failed password attempts increment no access metrics and return `HTTP 401 Unauthorized` with error code `INVALID_CREDENTIALS`.

### 2.4 Last-Owner Defense
- The workspace role modification and member deletion APIs enforce an invariant preventing demoting or removing the sole remaining workspace Owner.

### 2.5 Input Sanitization & Anti-XSS
- Comment contents are HTML-escaped via `html.escape()` prior to storage and broadcast.
- Links and action URLs are validated to prevent `javascript:` scheme attacks.

