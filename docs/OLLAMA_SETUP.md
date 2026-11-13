# Local Ollama Integration & Setup Guide

## 1. Overview
DataLens supports local, self-hosted LLM execution through [Ollama](https://ollama.ai). This provides 100% data sovereignty, zero egress to external third-party cloud services, air-gapped compliance, and deterministic execution for enterprise installations.

---

## 2. Recommended Models
DataLens is optimized for modern open-weights instruction-tuned models:

| Model | Size | Minimum VRAM / RAM | Primary Use Cases | Recommended Command |
| :--- | :--- | :--- | :--- | :--- |
| **`gemma3:4b`** *(Recommended Default)* | ~2.5 GB | 4 GB VRAM / 8 GB RAM | Schema explanation, basic DuckDB SQL, queries | `ollama run gemma3:4b` |
| **`llama3.2:3b`** | ~2.0 GB | 4 GB VRAM / 8 GB RAM | Fast query routing, sentiment, simple summaries | `ollama run llama3.2:3b` |
| **`qwen2.5-coder:7b`** | ~4.7 GB | 8 GB VRAM / 16 GB RAM | Advanced SQL query synthesis, ML explanations | `ollama run qwen2.5-coder:7b` |
| **`mistral:7b`** | ~4.1 GB | 8 GB VRAM / 16 GB RAM | Deep business report generation, narratives | `ollama run mistral:7b` |

---

## 3. Installation & Setup on Windows

### Step 1: Download & Install Ollama
Download and run the Windows installer from the official website:
```powershell
winget install Ollama.Ollama
```
Or download directly from [https://ollama.com/download/windows](https://ollama.com/download/windows).

### Step 2: Start Ollama Daemon
Ensure the Ollama background service is running on its default host and port (`http://localhost:11434`):
```powershell
ollama serve
```
Verify the daemon is alive:
```powershell
curl http://localhost:11434/api/tags
```

### Step 3: Pull the Recommended Model
Pull Google's compact instruction model:
```powershell
ollama pull gemma3:4b
```

---

## 4. DataLens Configuration
In your DataLens `.env` or backend environment settings:
```env
# AI Routing Mode: "HYBRID", "LOCAL_ONLY", "GEMINI_ONLY", or "DETERMINISTIC_ONLY"
AI_ROUTING_MODE=HYBRID

# Ollama Endpoint Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT_SECONDS=60.0
OLLAMA_TEMPERATURE=0.1
```

---

## 5. Architectural Implementation
The [`OllamaProvider`](file:///d:/PE%20CP/backend/app/services/ai/ollama_provider.py) connects directly to Ollama's native REST endpoints using asynchronous HTTP (`httpx.AsyncClient`):

- **Health Check & Discovery (`GET /api/tags`):**
  Discovers all downloaded local models and determines latency.
- **Text Generation (`POST /api/generate`):**
  Executes streaming or non-streaming prompts with model context length control and stop sequences.
- **Structured JSON Mode:**
  Passes `format: "json"` to Ollama, enforcing schema compliance and parsing output directly into validated Pydantic models.
- **Offline Resilience:**
  If the daemon is offline or crashes, `OllamaProvider` gracefully reports `healthy: false` without throwing unhandled exceptions, enabling `HybridAIRouter` to fall back instantly to `DeterministicAIProvider`.

