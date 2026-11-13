# Phase 6A Known Limitations & Operational Considerations

## 1. Hardware Requirements for Local Ollama Models
- **VRAM vs. System RAM:**
  When executing models locally using Ollama on CPU instead of an NVIDIA/AMD GPU with CUDA/ROCm, inference latency can increase from ~25ms/token to ~250–500ms/token.
  - Recommended minimum GPU: 4 GB VRAM for `gemma3:4b` or `llama3.2:3b`.
  - For larger models (`qwen2.5-coder:7b` or `mistral:7b`), at least 8 GB VRAM is recommended.
- **Context Window Constraints:**
  Local compact models generally perform best within 4,096 to 8,192 token contexts. For massive datasets with hundreds of columns, schemas should be pruned or chunked before passing to local models.

---

## 2. Token Counting Approximation
- **Local vs Cloud Tokenizers:**
  Gemini provides native token count metadata in API responses. For local Ollama models, token counting is estimated based on Byte-Pair Encoding (BPE) character ratios (~3.8 characters per token) unless Ollama's `eval_count` is explicitly populated.

---

## 3. Streaming vs. Non-Streaming Structured Output
- Structured JSON outputs (`generate_structured_output`) operate in non-streaming mode to validate the complete JSON payload against Pydantic schema constraints before returning to the UI.
- Text narrative generation (`generate_text`) can support streaming, but batch reporting processes intentionally buffer the complete text to ensure formatting completeness before compiling into PDF/DOCX reports.

---

## 4. Multi-Tenant Air-Gapped Environments
- In strictly air-gapped deployments where outbound internet access is physically disabled, `AI_ROUTING_MODE` must be configured to `LOCAL_ONLY` or `DETERMINISTIC_ONLY`. Attempting to ping Gemini endpoints in an air-gapped network will produce DNS lookup timeouts before cascading to local models.

