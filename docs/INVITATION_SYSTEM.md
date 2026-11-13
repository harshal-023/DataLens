# DataLens – Workspace Invitation Lifecycle & Token Architecture

## 1. Overview
The workspace invitation system provides secure onboarding for new team members into shared workspaces with single-use tokens, email delivery, expiration enforcement, and status auditing.

---

## 2. Token Security Model
- **Token Generation**: 32-byte cryptographic entropy generated via `secrets.token_urlsafe(32)`.
- **Zero Raw Storage**: The raw token is delivered strictly to the invited recipient via email or UI copy link. The database stores only `token_hash = sha256(raw_token).hexdigest()`.
- **Single-Use Invalidation**: Upon acceptance or revocation, `is_accepted = True` and `status` transitions to `accepted` or `revoked`, permanently invalidating the token.

---

## 3. Invitation Status Transitions
```
                [ Created ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    [ Pending ]             [ Revoked ]
         │
    ┌────┴────────────┬────────────────┐
    ▼                 ▼                ▼
[ Accepted ]     [ Declined ]     [ Expired ]
```

1. **`pending`**: Invitation dispatched; waiting for recipient action.
2. **`accepted`**: User claimed invitation and joined workspace with assigned role.
3. **`declined`**: Recipient explicitly declined the invitation.
4. **`expired`**: Exceeded `INVITATION_TOKEN_EXPIRE_DAYS` (default 7 days).
5. **`revoked`**: Workspace Owner/Admin invalidated the pending invite before acceptance.

---

## 4. API Endpoints
- `POST /api/v1/workspaces/{workspace_id}/invitations`: Create and send new invitation.
- `GET /api/v1/workspaces/{workspace_id}/invitations`: List workspace invitations with status filters.
- `POST /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/resend`: Refresh token expiration and increment `resend_count`.
- `DELETE /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}`: Revoke active invitation.
- `GET /api/v1/invitations/{token}`: Inspect invitation public details without login.
- `POST /api/v1/invitations/{token}/accept`: Accept invitation for current user.
- `POST /api/v1/invitations/{token}/decline`: Decline invitation.

