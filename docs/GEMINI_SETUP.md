# DataLens — Google Gemini API Setup Guide

This guide provides step-by-step instructions for configuring Google Gemini as the primary and sole active LLM provider in DataLens.

---

## 1. Obtain a Google Gemini API Key

1. Navigate to **Google AI Studio**: [https://aistudio.google.com/](https://aistudio.google.com/)
2. Sign in with your Google account.
3. Click on **"Get API key"** in the top-left navigation.
4. Click **"Create API key"** (select an existing Google Cloud project or create a new one).
5. Copy your generated API key (format starts with `AIzaSy...`).

> **Security Note:** Never share, commit, or expose your API key. DataLens reads the key strictly from the server-side backend environment and never leaks it to the frontend or browser.

---

## 2. Configure Backend Environment

Open or create `backend/.env` in your project root:

```env
# AI Provider Configuration (Google Gemini)
AI_PROVIDER="gemini"
GEMINI_API_KEY="AIzaSyYourActualGoogleGeminiKeyHere"
GEMINI_MODEL="gemini-2.5-flash"
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=2
AI_ENABLED=true
AI_SEND_SAMPLE_VALUES=false
```

### Parameter Reference:
- `AI_PROVIDER`: Set to `gemini` (sole active provider).
- `GEMINI_API_KEY`: Your private Google Gemini API key.
- `GEMINI_MODEL`: Supported Google Gemini model (default: `gemini-2.5-flash`, optional: `gemini-2.5-pro`).
- `AI_TIMEOUT_SECONDS`: Request timeout in seconds (default: `30`).
- `AI_MAX_RETRIES`: Number of automatic retries with exponential backoff on transient errors (default: `2`).
- `AI_ENABLED`: Set to `true` to activate live Gemini parsing and synthesis.
- `AI_SEND_SAMPLE_VALUES`: Set to `false` (default) for maximum privacy. When `false`, zero raw cell data is transmitted to Gemini—only column names, inferred data types, and deterministic calculation aggregates.

---

## 3. Verify Local Connectivity

Run the backend verification command:

```powershell
backend\.venv\Scripts\python.exe -c "
import asyncio
from app.services.ai.factory import AIProviderFactory

async def check():
    provider = AIProviderFactory.get_provider()
    operational, err = await provider.check_availability()
    print('Operational:', operational)
    if err:
        print('Status message:', err)

asyncio.run(check())
"
```

If the key is valid, the output will display:
```
Operational: True
```

If `GEMINI_API_KEY` is not yet configured, DataLens automatically activates its deterministic fallback engine, ensuring all analytical calculations (DuckDB queries, forecasting, anomaly detection, segmentation) continue without error.

