from collections import defaultdict
from typing import Any

from app.schemas.prompt_lab import ExperimentComparisonResponse, VersionMetricSummary


class PromptAnalyticsService:
    """
    Computes comparative analytics across prompt versions in an experiment.
    Clearly indicates sample sizes and avoids premature statistical superiority claims.
    """

    @classmethod
    def compute_comparison(
        cls,
        experiment_id: Any,
        experiment_name: str,
        runs: list[Any],
        versions: dict[str, int],  # version_id_str -> version_number
    ) -> ExperimentComparisonResponse:
        """
        Aggregates runs and evaluations per prompt version.
        """
        version_runs = defaultdict(list)
        for run in runs:
            v_id = str(run.prompt_version_id)
            version_runs[v_id].append(run)

        version_summaries: list[VersionMetricSummary] = []

        for v_id, r_list in version_runs.items():
            v_num = versions.get(v_id, 1)
            total_runs = len(r_list)
            successful = [r for r in r_list if r.status == "completed"]
            failed = [r for r in r_list if r.status == "failed"]
            success_rate = (len(successful) / total_runs) * 100 if total_runs > 0 else 0.0

            # Latency
            latencies = [r.latency_ms for r in successful if r.latency_ms is not None]
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

            # Tokens
            inp_tokens = [r.input_tokens for r in successful if r.input_tokens is not None]
            avg_inp = sum(inp_tokens) / len(inp_tokens) if inp_tokens else None

            out_tokens = [r.output_tokens for r in successful if r.output_tokens is not None]
            avg_out = sum(out_tokens) / len(out_tokens) if out_tokens else None

            # Cost
            costs = [r.estimated_cost_usd for r in successful if r.estimated_cost_usd is not None]
            tot_cost = sum(costs) if costs else None

            # Evaluation scores
            all_scores = []
            metric_totals = defaultdict(list)
            for r in successful:
                for ev in getattr(r, "evaluation_results", []):
                    metric_totals[ev.metric_name].append(ev.score)
                    all_scores.append(ev.score)

            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            metric_averages = {m: round(sum(s) / len(s), 3) for m, s in metric_totals.items()}

            version_summaries.append(
                VersionMetricSummary(
                    version_id=v_id,
                    version_number=v_num,
                    runs_count=total_runs,
                    successful_runs=len(successful),
                    failed_runs=len(failed),
                    success_rate=round(success_rate, 1),
                    avg_latency_ms=round(avg_lat, 1),
                    avg_input_tokens=round(avg_inp, 1) if avg_inp is not None else None,
                    avg_output_tokens=round(avg_out, 1) if avg_out is not None else None,
                    total_cost_usd=round(tot_cost, 6) if tot_cost is not None else None,
                    avg_overall_score=round(avg_score, 3),
                    metric_scores=metric_averages,
                )
            )

        # Sort by version number
        version_summaries.sort(key=lambda s: s.version_number)

        # Determine best version if evidence exists
        best_v_id = None
        rationale = None
        observations = []

        if len(version_summaries) >= 2:
            # Sort by overall score, then latency
            candidates = [s for s in version_summaries if s.runs_count > 0]
            if candidates:
                best = max(candidates, key=lambda s: (s.avg_overall_score, s.success_rate, -s.avg_latency_ms))
                best_v_id = best.version_id

                total_observations = sum(s.runs_count for s in candidates)
                if total_observations < 5:
                    rationale = f"Version {best.version_number} scored highest ({best.avg_overall_score:.2f}), but observation count ({total_observations} runs) is too small for statistical significance."
                else:
                    rationale = f"Version {best.version_number} demonstrated superior performance with an average evaluation score of {best.avg_overall_score:.2f} and {best.success_rate:.0f}% success rate."

                # Observations
                v1 = version_summaries[0]
                v_best = best
                if v_best.version_id != v1.version_id:
                    score_diff = v_best.avg_overall_score - v1.avg_overall_score
                    observations.append(f"Version {v_best.version_number} achieved a +{score_diff:.2f} score delta over Version {v1.version_number}.")
                observations.append(f"Fastest version: Version {min(candidates, key=lambda s: s.avg_latency_ms).version_number} ({min(s.avg_latency_ms for s in candidates):.0f} ms).")
        elif len(version_summaries) == 1:
            best_v_id = version_summaries[0].version_id
            rationale = f"Single version evaluated (Version {version_summaries[0].version_number}). Add more versions to run comparative benchmarking."

        return ExperimentComparisonResponse(
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            total_test_cases=len(runs) // max(1, len(version_summaries)),
            versions_compared=version_summaries,
            best_version_id=best_v_id,
            best_version_rationale=rationale,
            observations=observations,
        )

