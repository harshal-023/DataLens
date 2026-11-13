"""Workflow DAG orchestration service: cycle detection, topological sorting, and dependency management."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from app.schemas.automation import WorkflowStepCreate, WorkflowValidationResponse

logger = logging.getLogger("datalens.automation.workflow")


class WorkflowDAGService:
    """Validates and sequences DAG steps for workflow execution."""

    @classmethod
    def validate_and_sort_steps(
        cls,
        steps: list[WorkflowStepCreate] | list[Any],
    ) -> WorkflowValidationResponse:
        """Validate workflow steps for missing dependencies, self-dependencies, and circular cycles.

        Returns topological order of step identifiers if valid.
        """
        errors: list[str] = []
        if not steps:
            return WorkflowValidationResponse(is_valid=True, errors=[], topological_order=[])

        # Step map
        step_id_map: dict[str, Any] = {}
        for idx, s in enumerate(steps):
            # If step has an id attribute (ORM), use it; otherwise use str(idx) or step_name
            sid = str(getattr(s, "id", None) or getattr(s, "step_name", str(idx)))
            step_id_map[sid] = s

        # Build in-degree and adjacency
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {sid: 0 for sid in step_id_map}

        for sid, s in step_id_map.items():
            deps = getattr(s, "depends_on_step_ids", []) or []
            for dep in deps:
                dep_str = str(dep)
                if dep_str == sid:
                    errors.append(f"Step '{getattr(s, 'step_name', sid)}' cannot depend on itself.")
                    continue
                if dep_str not in step_id_map:
                    errors.append(f"Step '{getattr(s, 'step_name', sid)}' references unknown prerequisite '{dep_str}'.")
                    continue
                adj[dep_str].append(sid)
                in_degree[sid] += 1

        if errors:
            return WorkflowValidationResponse(is_valid=False, errors=errors, topological_order=[])

        # Kahn's algorithm for topological sort and cycle detection
        queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
        topological_order: list[str] = []

        while queue:
            node = queue.popleft()
            topological_order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topological_order) != len(step_id_map):
            cycle_nodes = [getattr(step_id_map[sid], "step_name", sid) for sid, deg in in_degree.items() if deg > 0]
            errors.append(f"Circular dependency detected among workflow steps: {', '.join(cycle_nodes)}")
            return WorkflowValidationResponse(is_valid=False, errors=errors, topological_order=[])

        return WorkflowValidationResponse(
            is_valid=True,
            errors=[],
            topological_order=topological_order,
        )

    @classmethod
    def get_runnable_steps(
        cls,
        step_executions: dict[str, str],  # step_id -> status
        step_dependencies: dict[str, list[str]],  # step_id -> [dep_step_id]
        failure_policy: str = "STOP_IMMEDIATELY",
    ) -> list[str]:
        """Determine which PENDING steps are ready to execute based on upstream dependency statuses and failure policy."""
        runnable: list[str] = []
        has_failed_upstream = any(st in ("FAILED", "CANCELLED") for st in step_executions.values())

        if has_failed_upstream and failure_policy == "STOP_IMMEDIATELY":
            return []

        for sid, status in step_executions.items():
            if status != "PENDING":
                continue

            deps = step_dependencies.get(sid, [])
            # All prerequisites must be SUCCESS
            deps_satisfied = True
            for dep in deps:
                dep_status = step_executions.get(dep, "PENDING")
                if dep_status != "SUCCESS":
                    deps_satisfied = False
                    break

            if deps_satisfied:
                runnable.append(sid)

        return runnable
