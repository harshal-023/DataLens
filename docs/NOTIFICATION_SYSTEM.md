# DataLens – Notification System & Real-Time Delivery

## 1. Overview
The Notification System alerts team members to critical analytical events—such as shared dashboards, assigned reports, comments, @mentions, and workspace invitation updates—across both in-app and email channels with customizable user preferences.

---

## 2. Event Dispatch Pipeline
```
[ Triggering Event ] (e.g. @mention in comment, resource shared)
       │
       ▼
[ Self-Notification Check ] (Actor == Recipient ? Suppress : Continue)
       │
       ▼
[ Preference Evaluation ] (Query NotificationPreference for recipient)
       ├── In-App Enabled ──► Insert into `notifications` table ──► Broadcast to SSE Listeners
       └── Email Enabled  ──► DevEmailAdapter.send_notification_email()
```

---

## 3. Real-Time Server-Sent Events (SSE) Stream
- **Endpoint**: `GET /api/v1/notifications/stream`
- **Protocol**: `text/event-stream` with keep-alive heartbeats every 15 seconds.
- **In-Memory Pub/Sub**: `CollaborationService._notification_listeners` maps `user_id` to `asyncio.Queue` subscribers.
- **Frontend Fallback**: The client establishes an `EventSource` connection on mount and falls back to periodic 30-second polling if disconnected.

---

## 4. User Preferences
Users can independently toggle notification delivery for each channel and category:
- `email_notifications` (Boolean)
- `in_app_notifications` (Boolean)
- `mention_notifications` (Boolean)
- `share_notifications` (Boolean)

---

## 5. API Endpoints
- `GET /api/v1/notifications`: List notifications with unread filter and pagination.
- `GET /api/v1/notifications/unread-count`: Fetch current unread badge count.
- `PATCH /api/v1/notifications/{notification_id}/read`: Mark notification as read.
- `POST /api/v1/notifications/mark-all-read`: Mark all notifications as read.
- `DELETE /api/v1/notifications/{notification_id}`: Dismiss/delete notification.
- `GET /api/v1/notifications/preferences`: Get current user notification preferences.
- `PUT /api/v1/notifications/preferences`: Update preferences.
- `GET /api/v1/notifications/stream`: Real-time SSE notification stream.

