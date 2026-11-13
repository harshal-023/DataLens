import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402
from app.services.ai.factory import AIProviderFactory  # noqa: E402
from app.services.ai.gemini_provider import GeminiProvider  # noqa: E402


async def run_live_probe():
    print("=" * 60)
    print("DataLens Stage 8: Live Google Gemini Verification Probe")
    print("=" * 60)
    print(f"Configured Provider: {settings.AI_PROVIDER}")
    print(f"Configured Model:    {settings.effective_ai_model}")
    print(f"API Key Present:     {bool(settings.effective_ai_api_key)}")
    print(f"API Key Length:      {len(settings.effective_ai_api_key) if settings.effective_ai_api_key else 0}")
    print(f"API Key Prefix:      {settings.effective_ai_api_key[:4] if settings.effective_ai_api_key else 'None'}")
    print("-" * 60)

    # 1. Provider Instantiation
    provider = AIProviderFactory.get_provider()
    print(f"Instantiated Provider Class: {provider.__class__.__name__}")
    
    if not isinstance(provider, GeminiProvider):
        print(f"ERROR: Expected GeminiProvider, got {type(provider).__name__}")
        return False

    # 2. Availability Check
    print("\n[Step 1] Checking provider availability via models.get()...")
    is_available, reason = await provider.check_availability()
    print(f"Availability Status: {'AVAILABLE' if is_available else 'UNAVAILABLE'}")
    if reason:
        print(f"Status Detail: {reason}")

    if not is_available:
        print("\n--> Live Gemini API check failed authentication or connectivity.")
        print("--> Note: Google AI Studio API keys typically begin with 'AIzaSy...'.")
        print("--> The provided key was rejected by Google Gemini endpoint.")
        return False

    # 3. Text Generation Test
    print("\n[Step 2] Testing basic text generation (prompt: 'Reply with DataLens Gemini Live OK')...")
    try:
        text_resp = await provider.generate_text("Reply with exactly: DataLens Gemini Live OK")
        print(f"Response: {text_resp['text']}")
        print(f"Latency:  {text_resp['latency_ms']} ms")
        print(f"Tokens:   Input={text_resp['input_tokens']}, Output={text_resp['output_tokens']}")
        print(f"Provider: {text_resp['provider']} ({text_resp['model']})")
        print("Step 2 PASSED.")
    except Exception as e:
        print(f"Step 2 FAILED: {type(e).__name__}: {e}")
        return False

    # 4. Analytical Plan Generation Test
    print("\n[Step 3] Testing generate_plan()...")
    schema_metadata = {
        "columns": [
            {"name": "sales", "data_type": "FLOAT"},
            {"name": "category", "data_type": "VARCHAR"},
            {"name": "order_date", "data_type": "DATE"}
        ]
    }
    try:
        plan = await provider.generate_plan(
            question="What is the total sales by category?",
            schema_metadata=schema_metadata
        )
        print(f"Generated Intent: {plan.get('intent')}")
        print(f"Target Column:    {plan.get('target_column')}")
        print(f"Group By:         {plan.get('group_by_column')}")
        print(f"Aggregation:      {plan.get('aggregation')}")
        print(f"Confidence:       {plan.get('confidence')}")
        print("Step 3 PASSED.")
    except Exception as e:
        print(f"Step 3 FAILED: {type(e).__name__}: {e}")
        return False

    # 5. Structured Output Test
    print("\n[Step 4] Testing generate_structured()...")
    try:
        structured = await provider.generate_structured(
            prompt="Generate a JSON object with keys: headline (string), status (operational), and score (integer from 1 to 100).",
            system_instruction="You are a JSON generator. Return valid JSON only."
        )
        print(f"Structured Result: {structured}")
        print("Step 4 PASSED.")
    except Exception as e:
        print(f"Step 4 FAILED: {type(e).__name__}: {e}")
        return False

    # 6. Explanation Generation Test
    print("\n[Step 5] Testing generate_explanation()...")
    try:
        explanation = await provider.generate_explanation(
            question="What is the total sales by category?",
            plan={"intent": "group_by", "target_column": "sales", "group_by_column": "category"},
            results_summary={"Furniture": 45000.0, "Technology": 89000.0, "Office Supplies": 32000.0},
            evidence={"row_count": 3, "dataset_version": 1}
        )
        print(f"Explanation: {explanation}")
        print("Step 5 PASSED.")
    except Exception as e:
        print(f"Step 5 FAILED: {type(e).__name__}: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL LIVE GEMINI VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_live_probe())
    sys.exit(0 if success else 1)
