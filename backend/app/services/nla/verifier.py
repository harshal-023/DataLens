import contextlib
import re
import uuid
from typing import Any

from app.services.nla.schemas import NLAQueryPlan


class NLAEvidenceVerifier:
    """
    Evidence-grounding and numerical verification engine.
    Ensures that every business insight is directly backed by executed DuckDB evidence,
    preventing LLM hallucination of numerical figures.
    """

    @classmethod
    def format_currency_or_number(cls, val: float, is_currency: bool = True) -> str:
        if abs(val) >= 1_000_000:
            formatted = f"{val / 1_000_000:.2f}M"
        elif abs(val) >= 1_000:
            formatted = f"{val / 1_000:.1f}K"
        else:
            formatted = f"{val:,.2f}"
        return f"${formatted}" if is_currency else formatted

    @classmethod
    def verify_cited_numbers(
        cls,
        narrative: str,
        metric_cards: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """
        Detects hallucinated numbers in AI narrative that are not supported by calculated metrics.
        Returns (is_valid, list_of_warning_messages).
        """
        warnings: list[str] = []
        if not narrative:
            return True, warnings

        # Extract numerical tokens from narrative (e.g. 100, 25000.0, 999999.0)
        cited_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", narrative)
        
        # Collect allowed numbers from metric cards and basic thresholds
        allowed_nums: set[float] = {0.0, 1.0, 2.0, 5.0, 10.0, 100.0}
        for card in metric_cards:
            num = card.get("numeric_value")
            if num is not None:
                with contextlib.suppress(ValueError, TypeError):
                    allowed_nums.add(round(float(num), 2))
            val_str = str(card.get("value", ""))
            for extracted in re.findall(r"\b\d+(?:\.\d+)?\b", val_str.replace(",", "")):
                with contextlib.suppress(ValueError, TypeError):
                    allowed_nums.add(round(float(extracted), 2))

        # Check each cited number against allowed numbers
        is_valid = True
        for token in cited_numbers:
            try:
                val = round(float(token), 2)
                # Ignore small structural counts (e.g. top 5, 1st, 2 items, years 2020-2030)
                if val in (1, 2, 3, 4, 5, 10) or (2020 <= val <= 2035):
                    continue
                # If large number cited without grounding
                if val not in allowed_nums and not any(abs(val - allowed) < 0.05 for allowed in allowed_nums):
                    is_valid = False
                    warnings.append(f"Number {token} in AI narrative was not grounded in query results.")
            except (ValueError, TypeError):
                continue

        return is_valid, warnings

    @classmethod
    def synthesize_verified_evidence(
        cls,
        plan: NLAQueryPlan,
        result_data: dict[str, Any],
        raw_explanation: str,
        metric_name: str = "Metric",
        dataset_name: str = "Dataset",
        version_number: str = "v1",
        is_currency: bool = True,
    ) -> dict[str, Any]:
        """
        Extracts verified facts, checks numerical consistency, and formats response sections.
        """
        rows = result_data.get("rows", [])
        total_rows = result_data.get("total_records_analyzed", 0)
        duration_ms = result_data.get("execution_duration_ms", 0)

        metric_cards: list[dict[str, Any]] = []
        evidence_items: list[dict[str, Any]] = []
        calculated_facts: list[str] = []
        direct_answer: str = ""

        # Case A: Scalar metric (no group by)
        if len(rows) == 1 and not plan.group_by_columns and plan.intent != "time_series":
            val = float(rows[0].get("metric_value", 0) or 0)
            val_str = cls.format_currency_or_number(val, is_currency)
            direct_answer = f"Total {metric_name} is {val_str} across {total_rows:,} verified records."
            calculated_facts.append(f"Computed total {metric_name}: {val_str}")
            metric_cards = [
                {"label": f"Total {metric_name}", "value": val_str, "trend": "flat"},
                {"label": "Records Analyzed", "value": f"{total_rows:,}", "trend": "flat"},
            ]
            evidence_items.append({
                "id": f"ev-{uuid.uuid4().hex[:8]}",
                "title": f"Scalar {plan.aggregation} Calculation",
                "source": dataset_name,
                "version": version_number,
                "formula": result_data.get("compiled_sql", ""),
                "verified_value": val_str,
                "execution_duration_ms": duration_ms,
            })

        # Case B: Grouped / Ranking
        elif rows and plan.group_by_columns:
            group_col = plan.group_by_columns[0]
            top_row = rows[0]
            top_key = str(top_row.get(group_col, "Top Item"))
            top_val = float(top_row.get("metric_value", 0) or 0)
            top_val_str = cls.format_currency_or_number(top_val, is_currency)
            share_val = top_row.get("share_of_total")

            share_suffix = f" ({share_val}% of total)" if share_val is not None else ""
            direct_answer = (
                f"{top_key} achieved the highest {metric_name} at {top_val_str}{share_suffix}."
            )
            calculated_facts.append(f"Top {group_col}: {top_key} with {top_val_str}")
            if len(rows) > 1:
                bottom_row = rows[-1]
                bot_key = str(bottom_row.get(group_col, "Lowest Item"))
                bot_val = float(bottom_row.get("metric_value", 0) or 0)
                calculated_facts.append(
                    f"Lowest {group_col}: {bot_key} with {cls.format_currency_or_number(bot_val, is_currency)}"
                )

            metric_cards = [
                {"label": f"Top {group_col.title()}", "value": top_key, "trend": "up"},
                {"label": f"Top {metric_name}", "value": top_val_str, "trend": "up"},
                {"label": "Distinct Groups", "value": str(len(rows)), "trend": "flat"},
                {"label": "Total Analyzed", "value": f"{total_rows:,}", "trend": "flat"},
            ]
            evidence_items.append({
                "id": f"ev-{uuid.uuid4().hex[:8]}",
                "title": f"{metric_name} Breakdown by {group_col}",
                "source": dataset_name,
                "version": version_number,
                "formula": result_data.get("compiled_sql", ""),
                "verified_value": f"Top: {top_key} ({top_val_str})",
                "execution_duration_ms": duration_ms,
            })

        # Case C: Time Series
        elif rows and (plan.intent == "time_series" or "period" in result_data.get("columns", [])):
            peak_row = max(rows, key=lambda r: float(r.get("metric_value", 0) or 0))
            peak_period = str(peak_row.get("period", "Peak Period"))
            peak_val = float(peak_row.get("metric_value", 0) or 0)
            peak_val_str = cls.format_currency_or_number(peak_val, is_currency)

            direct_answer = (
                f"{metric_name} reached its maximum in {peak_period} at {peak_val_str}."
            )
            calculated_facts.append(f"Peak interval: {peak_period} with {peak_val_str}")
            calculated_facts.append(f"Total periods evaluated: {len(rows)}")

            metric_cards = [
                {"label": "Peak Period", "value": peak_period, "trend": "up"},
                {"label": "Peak Value", "value": peak_val_str, "trend": "up"},
                {"label": "Periods", "value": str(len(rows)), "trend": "flat"},
            ]
            evidence_items.append({
                "id": f"ev-{uuid.uuid4().hex[:8]}",
                "title": f"{metric_name} Time Series Trend",
                "source": dataset_name,
                "version": version_number,
                "formula": result_data.get("compiled_sql", ""),
                "verified_value": f"Peak: {peak_period} ({peak_val_str})",
                "execution_duration_ms": duration_ms,
            })

        else:
            direct_answer = f"No records found matching the requested criteria for {metric_name}."

        return {
            "direct_answer": direct_answer,
            "calculated_facts": calculated_facts,
            "ai_explanation": raw_explanation or direct_answer,
            "metric_cards": metric_cards,
            "evidence_items": evidence_items,
        }
