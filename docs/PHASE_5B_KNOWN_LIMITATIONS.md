# DataLens – Phase 5B Known Limitations & Future Considerations

## 1. Known Limitations & Design Decisions

### 1.1 In-Memory Pub/Sub for Real-Time SSE
- **Current Behavior**: Real-time notifications use an in-memory `asyncio.Queue` registry within the active FastAPI process.
- **Limitation**: In horizontally scaled multi-instance deployments behind a load balancer, notifications triggered on Instance A will not reach clients connected to Instance B without a distributed pub/sub backbone (e.g., Redis Pub/Sub or PostgreSQL `LISTEN/NOTIFY`).
- **Mitigation**: A 30-second client-side polling fallback guarantees eventual delivery even if an SSE node disconnects or messages are routed across different nodes.

### 1.2 Dev Email Adapter in Local Development
- **Current Behavior**: By default, emails are logged to the console and in-memory buffer via `dev_email_adapter` unless SMTP environment variables are populated.
- **Production Readiness**: When SMTP/SES credentials are provided, `dev_email_adapter` seamlessly routes to the production email transport.

### 1.3 Comment Rich-Text Formatting
- **Current Behavior**: Comments support plain text, newlines, and `@mentions`, with strict HTML-escaping to prevent XSS. Markdown or rich WYSIWYG HTML formatting is deliberately disabled to enforce maximum security.

