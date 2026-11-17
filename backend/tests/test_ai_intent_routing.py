"""
Comprehensive test suite for DataLens AI Conversation Intelligence & Intent Routing.
Verifies that ordinary conversation (greetings, casual chat, capability queries, unsupported requests)
is cleanly distinguished from analytical questions before executing dataset queries.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.services.ai.intent_classifier import (
    ConversationalResponseBuilder,
    ConversationIntent,
    IntentClassifier,
)
from app.services.ai.orchestrator import AIAnalyticsOrchestrator

# =====================================================================
# 1. INTENT CLASSIFICATION UNIT TESTS FOR ALL 8 CATEGORIES
# =====================================================================


def test_intent_greeting_standalone():
    """Verify various greeting phrases without analytical context classify as GREETING."""
    greetings = [
        "hi",
        "Hi!",
        "hello",
        "Hello there",
        "hey",
        "Heya",
        "howdy",
        "good morning",
        "Good afternoon!",
        "good evening",
        "greetings",
        "yo",
        "sup",
    ]
    for g in greetings:
        assert IntentClassifier.classify(g) == ConversationIntent.GREETING, f"Failed for '{g}'"


def test_intent_casual_conversation():
    """Verify polite casual banter classifies as CASUAL_CONVERSATION."""
    phrases = [
        "thanks",
        "Thank you very much!",
        "thx",
        "appreciate it",
        "how are you?",
        "how are you doing",
        "how's it going",
        "nice",
        "cool",
        "great!",
        "awesome",
        "perfect",
        "okay",
        "ok",
        "got it",
        "sounds good",
        "bye",
        "goodbye",
        "who are you?",
    ]
    for p in phrases:
        assert IntentClassifier.classify(p) == ConversationIntent.CASUAL_CONVERSATION, f"Failed for '{p}'"


def test_intent_capability_query():
    """Verify capability inquiries classify as CAPABILITY_QUERY."""
    queries = [
        "what can you do",
        "What can you do?",
        "what are your capabilities",
        "how can you help me",
        "how can you help?",
        "help",
        "what features do you have",
        "what can I ask you",
        "how does this work?",
        "what is datalens?",
    ]
    for q in queries:
        assert IntentClassifier.classify(q) == ConversationIntent.CAPABILITY_QUERY, f"Failed for '{q}'"


def test_intent_unsupported_request():
    """Verify out-of-domain requests classify as UNSUPPORTED_REQUEST."""
    queries = [
        "write a poem about trees",
        "tell me a joke",
        "what's the weather in Seattle?",
        "weather in New York",
        "book a flight to Paris",
        "who won the world cup in 2022",
        "translate this to Spanish",
        "write a python script to scrape twitter",
        "who is the president of France?",
    ]
    for q in queries:
        assert IntentClassifier.classify(q) == ConversationIntent.UNSUPPORTED_REQUEST, f"Failed for '{q}'"


def test_intent_data_explanation():
    """Verify requests to explain metrics, columns, or charts classify as DATA_EXPLANATION."""
    queries = [
        "what does the sales column mean?",
        "what does revenue mean?",
        "explain this metric",
        "explain this chart",
        "how is revenue calculated?",
        "what is the difference between revenue and profit?",
        "explain this result",
    ]
    for q in queries:
        assert IntentClassifier.classify(q) == ConversationIntent.DATA_EXPLANATION, f"Failed for '{q}'"


def test_intent_clarification_ambiguous():
    """Verify vague or highly ambiguous queries classify as CLARIFICATION."""
    queries = [
        "sales?",
        "performance",
        "show me stats",
        "how are we doing",
        "tell me the numbers",
        "data?",
    ]
    for q in queries:
        assert IntentClassifier.classify(q) == ConversationIntent.CLARIFICATION, f"Failed for '{q}'"


def test_intent_contextual_follow_up():
    """Verify follow-up questions referencing prior turn classify as FOLLOW_UP."""
    history = [{"role": "user", "content": "Which product had highest revenue?"}]
    context = {"active_metric_name": "revenue", "last_intent": "ranking"}

    follow_ups = [
        "now break it down by region",
        "what about last month?",
        "and for product B?",
        "by category",
        "filter by North",
        "show that as a table",
        "compare that with 2024",
    ]
    for f in follow_ups:
        res = IntentClassifier.classify(
            f, conversation_history=history, active_context=context
        )
        assert res == ConversationIntent.FOLLOW_UP, f"Failed for '{f}'"


def test_intent_data_analysis():
    """Verify genuine business intelligence queries classify as DATA_ANALYSIS."""
    queries = [
        "Which product generated the highest revenue?",
        "Show monthly revenue trend for 2025",
        "Compare regional sales performance",
        "Total orders by customer segment",
        "Top 5 sales representatives by quota attainment",
        "Average fulfillment SLA across facilities",
        "Distribution of order values",
    ]
    for q in queries:
        assert IntentClassifier.classify(q) == ConversationIntent.DATA_ANALYSIS, f"Failed for '{q}'"


# =====================================================================
# 2. EDGE CASES & MIXED QUERY RESOLUTION
# =====================================================================


def test_mixed_greeting_and_analysis():
    """A greeting accompanied by an analytical question must route to DATA_ANALYSIS."""
    mixed_queries = [
        "Hello, show me the top products by revenue",
        "Hi, what was our total sales last quarter?",
        "Hey! Can you compare North vs South performance?",
        "Good morning, which category had the highest growth?",
    ]
    for q in mixed_queries:
        assert IntentClassifier.classify(q) == ConversationIntent.DATA_ANALYSIS, f"Failed for '{q}'"


def test_dataset_column_mention_overrides_unsupported():
    """If a query mentions an active dataset column, it should not be discarded as unsupported."""
    columns = ["revenue", "region", "product_name", "flight_booking_date"]
    res = IntentClassifier.classify(
        "show total for flight_booking_date by region", columns=columns
    )
    assert res == ConversationIntent.DATA_ANALYSIS


# =====================================================================
# 3. CONVERSATIONAL RESPONSE BUILDER TESTS
# =====================================================================


def test_conversational_response_builder_greeting_with_dataset():
    """Greeting response must acknowledge dataset and suggest questions without data artifacts."""
    res = ConversationalResponseBuilder.build_greeting_response(
        dataset_name="Sales_Data_2025",
        row_count=1240,
        suggested_questions=["Top product?", "Trend?"],
    )
    assert res["intent"] == "GREETING"
    assert "Sales_Data_2025" in res["direct_answer"]
    assert "1,240" in res["direct_answer"]
    assert res["metric_cards"] == []
    assert res["chart_data"] is None
    assert res["table_data"] is None
    assert res["evidence_items"] == []
    assert len(res["suggested_follow_ups"]) >= 2


def test_conversational_response_builder_casual():
    """Casual response must be natural and contain zero data artifacts."""
    res = ConversationalResponseBuilder.build_casual_response("thank you so much")
    assert res["intent"] == "CASUAL_CONVERSATION"
    assert "welcome" in res["direct_answer"].lower()
    assert res["metric_cards"] == []
    assert res["evidence_items"] == []


def test_conversational_response_builder_capability():
    """Capability response must list structured bullet points and suggested questions."""
    res = ConversationalResponseBuilder.build_capability_response(
        dataset_name="Financials_Q4",
        suggested_questions=["Top items?", "Monthly trend?"],
    )
    assert res["intent"] == "CAPABILITY_QUERY"
    assert "Metric Calculations" in res["direct_answer"]
    assert "Time-Series" in res["direct_answer"]
    assert "Visual Insights" in res["direct_answer"]
    assert res["metric_cards"] == []
    assert res["evidence_items"] == []


def test_conversational_response_builder_unsupported():
    """Unsupported response must explain product scope boundaries politely."""
    res = ConversationalResponseBuilder.build_unsupported_response("write a song")
    assert res["intent"] == "UNSUPPORTED_REQUEST"
    assert "DataLens" in res["direct_answer"]
    assert "unable to assist" in res["direct_answer"]
    assert res["metric_cards"] == []
    assert res["chart_data"] is None


# =====================================================================
# 4. ORCHESTRATOR ROUTING BEHAVIOR (ZERO DUCKDB QUERY EXECUTION)
# =====================================================================


@pytest.mark.asyncio
async def test_orchestrator_routes_greeting_without_duckdb_execution():
    """Verify that calling process_question with 'Hello' never queries DuckDB or computes metrics."""
    mock_db = AsyncMock()
    mock_dataset = Dataset(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Enterprise_Sales_2025",
        original_filename="sales.parquet",
        file_type="parquet",
    )
    mock_version = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=mock_dataset.id,
        version_number=1,
        row_count=5000,
        storage_key="test/manifest.json",
    )
    columns_meta = [
        {"name": "region", "inferred_type": "string"},
        {"name": "revenue", "inferred_type": "numeric"},
    ]

    with patch("app.services.analytics.engine.AnalyticsEngine.compute_aggregation") as mock_agg:
        response = await AIAnalyticsOrchestrator.process_question(
            question="Hello DataLens!",
            dataset=mock_dataset,
            version=mock_version,
            parquet_paths=[],
            columns_meta=columns_meta,
            user_id=uuid.uuid4(),
            db=mock_db,
        )

        # Assert DuckDB aggregation was NEVER executed
        mock_agg.assert_not_called()

        # Assert clean conversational response
        assert response is not None
        assert response.metrics == []
        assert response.chart_data is None
        assert response.table_data is None
        assert response.evidence == []
        assert "Enterprise_Sales_2025" in response.direct_answer
        assert len(response.suggested_follow_ups) > 0


@pytest.mark.asyncio
async def test_orchestrator_routes_casual_chat_without_duckdb_execution():
    """Verify that 'thanks' returns conversational response without analytical computation."""
    mock_db = AsyncMock()
    mock_dataset = Dataset(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Financial_Metrics",
        original_filename="financials.parquet",
        file_type="parquet",
    )
    mock_version = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=mock_dataset.id,
        version_number=1,
        row_count=1000,
        storage_key="test/manifest.json",
    )

    with patch("app.services.analytics.engine.AnalyticsEngine.compute_aggregation") as mock_agg:
        response = await AIAnalyticsOrchestrator.process_question(
            question="Thanks a lot!",
            dataset=mock_dataset,
            version=mock_version,
            parquet_paths=[],
            columns_meta=[{"name": "amount", "inferred_type": "numeric"}],
            user_id=uuid.uuid4(),
            db=mock_db,
        )

        mock_agg.assert_not_called()
        assert response is not None
        assert response.metrics == []
        assert response.chart_data is None
        assert response.evidence == []
        assert "welcome" in response.direct_answer.lower()


@pytest.mark.asyncio
async def test_conversational_response_builder_async_gemini_mocked():
    """Verify build_conversational_response_async formats prompt and returns Gemini output."""
    class MockGemini:
        async def generate_text(self, *args, **kwargs):
            return {
                "text": "Hello! I am DataLens AI. How can I help you analyze your data today?",
                "latency_ms": 150,
                "model": "gemini-3.1-flash-lite",
                "provider": "gemini",
            }

    res = await ConversationalResponseBuilder.build_conversational_response_async(
        question="Hello there",
        intent=ConversationIntent.GREETING,
        dataset_name="Retail_Sales",
        row_count=5000,
        provider=MockGemini(),
    )

    assert res["provider"] == "gemini"
    assert res["model"] == "gemini-3.1-flash-lite"
    assert "DataLens AI" in res["direct_answer"]
    assert res["metric_cards"] == []
    assert res["chart_data"] is None


@pytest.mark.asyncio
async def test_conversational_response_builder_async_fallback_when_gemini_fails():
    """Verify build_conversational_response_async gracefully falls back to deterministic rules if Gemini errors."""
    class FailingGemini:
        async def generate_text(self, *args, **kwargs):
            raise Exception("API quota exceeded")

    res = await ConversationalResponseBuilder.build_conversational_response_async(
        question="What can you do?",
        intent=ConversationIntent.CAPABILITY_QUERY,
        dataset_name="Retail_Sales",
        provider=FailingGemini(),
    )

    assert res["provider"] == "deterministic_fallback"
    assert "Metric Calculations" in res["direct_answer"]
    assert res["metric_cards"] == []







