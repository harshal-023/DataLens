# DataLens 1.0 – Environment Configuration & Secret Management

## 1. Overview & Security Rules

To guarantee enterprise confidentiality:
- Actual secrets and `.env` files must **never** be committed to Git.
- Real credentials and API keys must **never** be printed in logs, console outputs, or build artifacts.
- In production, all variables must be configured via the hosting provider's secure Environment Settings dashboard (e.g. Render Dashboard, Cloudflare Pages Environment Variables).

---

## 2. Backend Environment Variables (`.env.example`)

```ini
# ==============================================================================
# DataLens Backend Configuration (Production Baseline)
# ==============================================================================

# Application Metadata
APP_NAME="DataLens Business Intelligence Platform"
APP_ENV="production"
DEBUG=false
API_V1_PREFIX="/api/v1"

# Database Connection (Neon / PostgreSQL Serverless)
# Format: postgresql+asyncpg://<username>:<password>@<neon-host>/<database>?ssl=require
DATABASE_URL="postgresql+asyncpg://datalens_user:your_secure_password@ep-cool-frost-123456.us-east-2.aws.neon.tech/datalens?ssl=require"
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true

# Security & Secret Signing
# Generate a random 64-character hex key using: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY="REPLACE_WITH_A_SECURE_64_CHARACTER_RANDOM_HEX_STRING"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Allowed CORS Origins (Comma-separated allowed frontend origins, NO trailing slash)
CORS_ORIGINS="https://datalens.pages.dev,http://localhost:5173"

# File Storage Configuration (Persistent S3 / Supabase Storage / Local NVMe)
STORAGE_ROOT="/var/lib/datalens/storage"
MAX_UPLOAD_SIZE_MB=50

# S3 / Object Storage Settings (If using Cloudflare R2 or Supabase Storage)
# S3_ENDPOINT_URL="https://your-project.supabase.co/storage/v1/s3"
# S3_ACCESS_KEY="your-s3-access-key"
# S3_SECRET_KEY="your-s3-secret-key"
# S3_BUCKET_NAME="datalens-parquet"
# S3_REGION="us-east-1"

# AI Provider Configuration
# Supported providers: 'deterministic', 'gemini', 'ollama', 'hybrid'
AI_PROVIDER="deterministic"
AI_ENABLED=true
AI_SEND_SAMPLE_VALUES=false

# Optional Google Gemini Free-Tier Key (Only if using AI_PROVIDER=gemini or hybrid)
# GEMINI_API_KEY="your-google-ai-studio-gemini-key"
# GEMINI_MODEL="gemini-1.5-flash"

# Optional Ollama Local AI Settings (Only if running a local Ollama server)
# OLLAMA_BASE_URL="http://127.0.0.1:11434"
# OLLAMA_MODEL="llama3"
```

---

## 3. Frontend Environment Variables (`.env.production`)

```ini
# ==============================================================================
# DataLens Frontend Production Configuration
# ==============================================================================

# Public API URL pointing to the deployed backend
# Example for Render: https://datalens-api.onrender.com
VITE_API_URL="https://your-backend-app.onrender.com"

# Application Title
VITE_APP_TITLE="DataLens Business Intelligence"
```

---

## 4. Secret Generation & Rotation Guidelines

1. **Generating a Cryptographically Secure `SECRET_KEY`**:
   Run the following command in terminal:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Rotating Secrets**:
   - If `SECRET_KEY` is rotated in production, active user sessions will be invalidated, requiring users to log in again.
   - Database credentials can be changed in Neon without affecting application code by updating `DATABASE_URL` in the Render environment variables dashboard.
