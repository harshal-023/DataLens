import re
from typing import Any

from app.core.exceptions import DataLensException

VARIABLE_REGEX = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


class PromptTemplateEngine:
    """
    Deterministic template parsing, variable extraction, and safe string rendering.
    """

    @staticmethod
    def extract_variables(template: str) -> list[str]:
        """
        Extract unique variable names from template string (e.g. {{customer_name}}).
        """
        if not template:
            return []
        matches = VARIABLE_REGEX.findall(template)
        # Preserve order while deduplicating
        seen = set()
        unique = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        return unique

    @staticmethod
    def validate_and_render(
        system_prompt: str,
        user_prompt_template: str,
        provided_variables: dict[str, Any],
        required_variables: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Validates required variables and safely renders both system and user prompt templates.
        Raises DataLensException if any required variable is missing.
        """
        detected_in_system = PromptTemplateEngine.extract_variables(system_prompt or "")
        detected_in_user = PromptTemplateEngine.extract_variables(user_prompt_template or "")
        all_detected = set(detected_in_system + detected_in_user)

        # Check required variables
        if required_variables:
            missing_required = [req for req in required_variables if req not in provided_variables or provided_variables[req] is None]
            if missing_required:
                raise DataLensException(
                    f"Missing required prompt variables: {', '.join(missing_required)}",
                    code="MISSING_PROMPT_VARIABLES",
                )

        # Also verify that every variable placeholder detected in the template has a value
        missing_detected = [v for v in all_detected if v not in provided_variables or provided_variables[v] is None]
        if missing_detected:
            raise DataLensException(
                f"Unpopulated variables in template: {', '.join(missing_detected)}",
                code="UNPOPULATED_TEMPLATE_VARIABLES",
            )

        # Safe string substitution
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            val = provided_variables.get(var_name, "")
            return str(val)

        rendered_system = VARIABLE_REGEX.sub(replace_var, system_prompt or "")
        rendered_user = VARIABLE_REGEX.sub(replace_var, user_prompt_template or "")

        return rendered_system, rendered_user

