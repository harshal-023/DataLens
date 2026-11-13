"""
Intent Classification and Conversational Intelligence Layer for DataLens AI Data Analyst.
Distinguishes ordinary conversation from analytical questions before executing dataset queries.
"""

from __future__ import annotations

import logging
import re
from enum import StrEnum
from typing import Any

logger = logging.getLogger("datalens.ai.intent")


class ConversationIntent(StrEnum):
    GREETING = "GREETING"
    CASUAL_CONVERSATION = "CASUAL_CONVERSATION"
    CAPABILITY_QUERY = "CAPABILITY_QUERY"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    DATA_EXPLANATION = "DATA_EXPLANATION"
    FOLLOW_UP = "FOLLOW_UP"
    CLARIFICATION = "CLARIFICATION"
    UNSUPPORTED_REQUEST = "UNSUPPORTED_REQUEST"


class IntentClassifier:
    """
    Classifies incoming user messages into conversational vs analytical intents.
    Uses high-precision deterministic rules first, followed by heuristic/AI classification.
    """

    # Deterministic regex patterns for greetings
    GREETING_PATTERNS = [
        r"^(hi|hello|hey|heya|howdy|good\s+(morning|afternoon|evening|day)|greetings|yo|sup|hiya)(\s+(datalens(\s+ai)?|there|assistant|bot|team|everyone))?[!.,\s]*$",
    ]

    # Casual conversational expressions
    CASUAL_PATTERNS = [
        r"^(thanks|thank\s+you|thx|thank\s+you\s+so\s+much|appreciate\s+it|many\s+thanks)[!.,\s]*$",
        r"^(how\s+are\s+you(\s+doing)?|how's\s+it\s+going|how\s+do\s+you\s+do)[?.,\s]*$",
        r"^(nice|cool|great|awesome|perfect|okay|ok|sounds\s+good|understood|got\s+it|alright|fine)[!.,\s]*$",
        r"^(good\s+job|well\s+done|nice\s+work|impressive|excellent)[!.,\s]*$",
        r"^(bye|goodbye|see\s+you(\s+later)?|have\s+a\s+good\s+day|cya)[!.,\s]*$",
        r"^(who\s+are\s+you|are\s+you\s+an?\s+ai|are\s+you\s+human|what\s+is\s+your\s+name)[?.,\s]*$",
    ]

    # Capability queries
    CAPABILITY_PATTERNS = [
        r"^(what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities|how\s+can\s+you\s+help(\s+me)?|what\s+do\s+you\s+do)[?.,\s]*$",
        r"^(help|help\s+me|what\s+features\s+do\s+you\s+have|what\s+can\s+i\s+ask(\s+you)?)[?.,\s]*$",
        r"^(how\s+does\s+this\s+work|how\s+do\s+i\s+use\s+this|what\s+is\s+datalens|tell\s+me\s+about\s+yourself)[?.,\s]*$",
    ]

    # Unsupported queries (outside BI and dataset analytics)
    UNSUPPORTED_PATTERNS = [
        r"(write\s+(a\s+)?(poem|story|song|essay|joke)|tell\s+me\s+a\s+joke)",
        r"(what('s|\s+is)\s+the\s+weather|weather\s+in\s+)",
        r"(book\s+a\s+(flight|hotel|ticket)|order\s+(food|a\s+pizza))",
        r"(who\s+won\s+the\s+(world\s+cup|super\s+bowl|election|match|game))",
        r"(translate\s+(this\s+)?(into|to)\s+[a-z]+)",
        r"(write\s+(a\s+)?(python|javascript|java|c\+\+)?\s*script\s+to\s+scrape)",
        r"(play\s+(music|a\s+song|video))",
        r"(who\s+is\s+the\s+(president|prime\s+minister)\s+of)",
        r"(what\s+is\s+the\s+capital\s+of\s+[a-z]+)",
    ]

    # Clarification / broad ambiguous queries
    AMBIGUOUS_PATTERNS = [
        r"^(show|tell|give)\s+(me\s+)?(the\s+)?(best\s+)?(sales|performance|numbers|data|stats|metrics)(\?)?$",
        r"^(sales|performance|analytics|numbers|data|stats)(\?)?\s*$",
        r"^(how\s+are\s+we\s+doing)(\?)?$",
        r"^(how\s+did\s+we\s+do)(\?)?$",
        r"^what\s+(is|about)\s+(the\s+)?(performance|sales|numbers)(\?)?$",
    ]

    # Data explanation patterns
    EXPLANATION_PATTERNS = [
        r"^(explain|describe|clarify|elaborate\s+on)\s+(this|the|my)?\s*(metric|chart|table|result|number|finding|column|calculation|data)?",
        r"^what\s+does\s+(the\s+)?[\w_\s]+\s+mean[?.,\s]*$",
        r"^what\s+is\s+(the\s+)?[\w_\s]+(\s+column|\s+metric)?[?.,\s]*$",
        r"^how\s+is\s+(the\s+)?[\w_\s]+\s+calculated[?.,\s]*$",
        r"^why\s+did\s+(the\s+)?[\w_\s]+\s+(drop|increase|fall|grow|change)[?.,\s]*$",
        r"^what\s+is\s+the\s+difference\s+between\s+[\w_\s]+\s+and\s+[\w_\s]+[?.,\s]*$",
    ]

    # Follow-up continuation patterns
    FOLLOW_UP_STARTERS = [
        r"^(and\s+|what\s+about\s+|how\s+about\s+|now\s+|break\s+(it\s+)?down\s+by\s+|by\s+|filter\s+(by\s+|for\s+)|for\s+|in\s+\d{4}|compare\s+(that\s+|this\s+)?with\s+|compare\s+to\s+|show\s+(that|it)\s+as\s+a\s+|why\s+did\s+it\s+|its\s+|for\s+it\s+)",
    ]

    # Analytical signal keywords
    ANALYTICAL_KEYWORDS = {
        "revenue", "sales", "total", "sum", "average", "avg", "mean", "median",
        "count", "min", "max", "top", "highest", "best", "rank", "ranking",
        "bottom", "lowest", "worst", "trend", "monthly", "daily", "quarterly",
        "yearly", "annual", "over time", "growth", "compare", "comparison",
        "versus", "vs", "breakdown", "group by", "grouped", "per", "distribution",
        "share", "percentage", "margin", "profit", "loss", "cost", "volume",
        "units", "quantity", "kpi", "performance", "sla", "attainment",
        "maximum", "minimum", "aggregate", "filter", "where",
    }

    @classmethod
    def classify(
        cls,
        question: str,
        conversation_history: list[dict[str, Any]] | None = None,
        active_context: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> ConversationIntent:
        """
        Main intent classification method.
        Evaluates message text, conversation history, and dataset context.
        """
        clean = question.strip()
        q_lower = clean.lower()

        # Remove trailing punctuation for matching
        q_norm = re.sub(r"[?!.,]+$", "", q_lower).strip()

        # 1. Check for obvious standalone Greetings first
        for pat in cls.GREETING_PATTERNS:
            if re.match(pat, q_norm):
                # Ensure no analytical request is embedded in the greeting
                if not cls._has_strong_analytical_intent(q_lower, columns):
                    return ConversationIntent.GREETING

        # 2. Check for Casual Conversation
        for pat in cls.CASUAL_PATTERNS:
            if re.match(pat, q_norm):
                if not cls._has_strong_analytical_intent(q_lower, columns):
                    return ConversationIntent.CASUAL_CONVERSATION

        # 3. Check for Capability Query
        for pat in cls.CAPABILITY_PATTERNS:
            if re.match(pat, q_norm) or ("what can you do" in q_lower) or ("how can you help" in q_lower):
                return ConversationIntent.CAPABILITY_QUERY

        # 4. Check for Unsupported Requests (outside BI domain)
        for pat in cls.UNSUPPORTED_PATTERNS:
            if re.search(pat, q_lower):
                # If question explicitly mentions dataset columns, it might be analytical
                if not cls._mentions_dataset_column(q_lower, columns):
                    return ConversationIntent.UNSUPPORTED_REQUEST

        # 5. Check for Data Explanation requests
        for pat in cls.EXPLANATION_PATTERNS:
            if re.search(pat, q_lower):
                return ConversationIntent.DATA_EXPLANATION

        # 6. Check for Clarification / Ambiguous queries
        for pat in cls.AMBIGUOUS_PATTERNS:
            if re.match(pat, q_norm):
                return ConversationIntent.CLARIFICATION

        # 7. Check for Contextual Follow-Up
        has_history = bool(conversation_history and len(conversation_history) > 0)
        has_active_context = bool(active_context and (active_context.get("active_metric_name") or active_context.get("last_intent")))

        if has_history or has_active_context:
            for pat in cls.FOLLOW_UP_STARTERS:
                if re.match(pat, q_lower):
                    return ConversationIntent.FOLLOW_UP
            # Short questions with pronouns referring to prior data
            if re.search(r"\b(it|its|that|those|them|this|the same)\b", q_lower) and len(q_lower.split()) <= 8:
                return ConversationIntent.FOLLOW_UP

        # 8. Check for Data Analysis (analytical keywords or column references)
        if cls._has_strong_analytical_intent(q_lower, columns):
            return ConversationIntent.DATA_ANALYSIS

        # 9. Fallback heuristic:
        # If words contain common questions about numbers or data, default to DATA_ANALYSIS
        if any(w in q_lower for w in ("how many", "which", "what was", "show me", "calculate", "find")):
            return ConversationIntent.DATA_ANALYSIS

        # Default fallback for unclassified general text
        if len(q_lower.split()) <= 4:
            return ConversationIntent.CASUAL_CONVERSATION

        return ConversationIntent.DATA_ANALYSIS

    @classmethod
    def _has_strong_analytical_intent(cls, q_lower: str, columns: list[str] | None = None) -> bool:
        """Determines if the text contains clear analytical operations or metrics."""
        words = set(re.findall(r"\b[a-z_0-9]+\b", q_lower))
        if words.intersection(cls.ANALYTICAL_KEYWORDS):
            return True

        if cls._mentions_dataset_column(q_lower, columns):
            return True

        # Look for multi-word phrases
        for phrase in ("over time", "group by", "broken down by", "top 5", "top 10", "share of total"):
            if phrase in q_lower:
                return True

        return False

    @classmethod
    def _mentions_dataset_column(cls, q_lower: str, columns: list[str] | None = None) -> bool:
        """Checks if any active dataset column is explicitly referenced in the user query."""
        if not columns:
            return False
        for col in columns:
            col_clean = col.lower().replace("_", " ")
            if col.lower() in q_lower or col_clean in q_lower:
                return True
        return False


class ConversationalResponseBuilder:
    """
    Constructs high-quality conversational responses for non-analytical intents
    (GREETING, CASUAL_CONVERSATION, CAPABILITY_QUERY, UNSUPPORTED_REQUEST, etc.)
    with zero DuckDB or dataset query execution.
    """

    @classmethod
    def build_greeting_response(
        cls,
        dataset_name: str | None = None,
        row_count: int | None = None,
        suggested_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Returns a friendly greeting acknowledging active dataset if present."""
        if dataset_name and row_count is not None and row_count > 0:
            direct_answer = (
                f"Hello! I'm your DataLens Business Intelligence Assistant. "
                f"I'm ready to help you analyze **{dataset_name}** ({row_count:,} records). "
                f"What business question would you like to explore today?"
            )
        elif dataset_name:
            direct_answer = (
                f"Hello! I'm your DataLens Business Intelligence Assistant. "
                f"I have **{dataset_name}** loaded and ready for analysis. "
                f"How can I help you with your data today?"
            )
        else:
            direct_answer = (
                "Hello! I'm your DataLens Business Intelligence Assistant. "
                "Select or upload a dataset to begin exploring metrics, trends, and business performance."
            )

        follow_ups = suggested_questions or [
            "Which product generated the highest revenue?",
            "Show monthly revenue trend",
            "Compare regional performance",
        ]

        return {
            "direct_answer": direct_answer,
            "content": direct_answer,
            "intent": ConversationIntent.GREETING.value,
            "metric_cards": [],
            "chart_data": None,
            "table_data": None,
            "evidence_items": [],
            "suggested_follow_ups": follow_ups[:3],
            "needs_clarification": False,
            "clarification_options": [],
        }

    @classmethod
    def build_casual_response(cls, question: str) -> dict[str, Any]:
        """Returns a polite, context-aware casual conversational response."""
        q_lower = question.lower().strip()

        if any(w in q_lower for w in ("thank", "thx", "appreciate")):
            direct_answer = (
                "You're very welcome! Let me know if you would like to explore any other metrics, "
                "examine trends over time, or create visualizations from your data."
            )
        elif any(w in q_lower for w in ("how are you", "how's it going", "how do you do")):
            direct_answer = (
                "I'm doing well, thank you! I'm ready to help you analyze your data and extract business insights. "
                "What would you like to evaluate?"
            )
        elif any(w in q_lower for w in ("bye", "goodbye", "see you")):
            direct_answer = (
                "Goodbye! Feel free to return anytime you need data analysis or business intelligence reports."
            )
        elif any(w in q_lower for w in ("who are you", "are you an ai", "what is your name")):
            direct_answer = (
                "I am DataLens AI, your specialized Business Intelligence and Data Analyst assistant. "
                "I calculate verified metrics, identify performance trends, and formulate visual insights from your data."
            )
        else:
            direct_answer = (
                "Understood! Whenever you're ready, feel free to ask a business or data question about your dataset."
            )

        return {
            "direct_answer": direct_answer,
            "content": direct_answer,
            "intent": ConversationIntent.CASUAL_CONVERSATION.value,
            "metric_cards": [],
            "chart_data": None,
            "table_data": None,
            "evidence_items": [],
            "suggested_follow_ups": [],
            "needs_clarification": False,
            "clarification_options": [],
        }

    @classmethod
    def build_capability_response(
        cls,
        dataset_name: str | None = None,
        suggested_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Returns a clear, structured summary of DataLens AI Analyst capabilities."""
        direct_answer = (
            "Here is what I can do as your DataLens Business Intelligence Assistant:\n\n"
            "• **Metric Calculations**: Compute sums, averages, totals, counts, and custom ratios across 100% of your records.\n"
            "• **Rankings & Breakdowns**: Discover top/bottom performers by category, region, sales rep, or any dimension.\n"
            "• **Time-Series Analysis**: Track growth trends across months, quarters, or days with peak identification.\n"
            "• **Visual Insights**: Generate grounded bar charts, line graphs, donut charts, and formatted tables.\n"
            "• **Verified Evidence**: Provide deterministic calculations with complete SQL audit transparency—zero hallucinated numbers.\n"
            "• **Executive Reporting**: Save findings to business reports and export results directly to CSV."
        )

        follow_ups = suggested_questions or [
            "Which product generated the highest revenue?",
            "Show monthly revenue trend",
            "Compare regional performance",
        ]

        return {
            "direct_answer": direct_answer,
            "content": direct_answer,
            "intent": ConversationIntent.CAPABILITY_QUERY.value,
            "metric_cards": [],
            "chart_data": None,
            "table_data": None,
            "evidence_items": [],
            "suggested_follow_ups": follow_ups[:4],
            "needs_clarification": False,
            "clarification_options": [],
        }

    @classmethod
    def build_unsupported_response(cls, question: str) -> dict[str, Any]:
        """Politely explains scope boundaries for requests outside BI & data analytics."""
        direct_answer = (
            "I am DataLens, your specialized Business Intelligence and Data Analyst assistant. "
            "My capabilities are focused on analyzing your uploaded datasets, calculating verified business metrics, "
            "and generating visual data insights.\n\n"
            "I'm unable to assist with external tasks like web browsing, creative writing, general trivia, or code scripting outside SQL analytics. "
            "How can I help you analyze your data?"
        )

        return {
            "direct_answer": direct_answer,
            "content": direct_answer,
            "intent": ConversationIntent.UNSUPPORTED_REQUEST.value,
            "metric_cards": [],
            "chart_data": None,
            "table_data": None,
            "evidence_items": [],
            "suggested_follow_ups": [],
            "needs_clarification": False,
            "clarification_options": [],
        }

    @classmethod
    def build_explanation_response(
        cls,
        question: str,
        columns_meta: list[dict[str, Any]] | None = None,
        previous_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Provides an explanation of a metric, column, or prior analytical result without running redundant queries."""
        q_lower = question.lower()
        cols = columns_meta or []

        # Check if asking about a specific column
        matched_col = None
        for col in cols:
            col_name = col.get("name", "")
            if col_name.lower() in q_lower or col_name.lower().replace("_", " ") in q_lower:
                matched_col = col
                break

        if matched_col:
            col_name = matched_col.get("name", "")
            col_type = matched_col.get("inferred_type", "text")
            samples = matched_col.get("sample_values", [])
            samples_str = f" Sample values include: {', '.join(str(s) for s in samples[:4])}." if samples else ""

            direct_answer = (
                f"The column **{col_name}** is stored as a **{col_type}** dimension. "
                f"It represents categorical or numerical data used for filtering and aggregation.{samples_str}"
            )
        elif previous_result:
            summary = previous_result.get("summary", "the previously computed analysis")
            direct_answer = (
                f"Regarding the previous finding: {summary}. "
                "All values were computed deterministically from your dataset."
            )
        else:
            direct_answer = (
                "DataLens calculations are computed deterministically directly from your dataset columns. "
                "Let me know if you would like me to explain a specific column or metric definition."
            )

        return {
            "direct_answer": direct_answer,
            "content": direct_answer,
            "intent": ConversationIntent.DATA_EXPLANATION.value,
            "metric_cards": [],
            "chart_data": None,
            "table_data": None,
            "evidence_items": [],
            "suggested_follow_ups": [f"Analyze {c.get('name', 'column')}" for c in cols[:3]],
            "needs_clarification": False,
            "clarification_options": [],
        }
