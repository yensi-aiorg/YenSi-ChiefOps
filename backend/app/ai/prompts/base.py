"""
Base prompt template with variable substitution.

All prompt templates in ChiefOps inherit from PromptTemplate.
Templates use Python string formatting with named placeholders,
e.g. ``{project_name}`` or ``{people_data}``.
"""

from __future__ import annotations

import re
from typing import Any


class PromptTemplate:
    """A reusable prompt template with named placeholders.

    Placeholders use Python's ``str.format_map`` syntax: ``{variable_name}``.
    Calling ``render(**kwargs)`` substitutes all provided variables and
    leaves any unmatched placeholders as empty strings.

    Attributes:
        template: The raw template string with ``{placeholder}`` markers.
        name: An optional human-readable name for logging and debugging.
    """

    def __init__(self, template: str, *, name: str = "") -> None:
        self.template = template
        self.name = name or self._derive_name()

    def render(self, **kwargs: Any) -> str:
        """Render the template by substituting all provided variables.

        Any placeholder not covered by ``kwargs`` is replaced with an
        empty string so the output never contains raw ``{placeholder}``
        markers.

        Args:
            **kwargs: Named values to substitute into the template.

        Returns:
            The fully rendered prompt string.
        """
        # Build a default dict that returns "" for missing keys
        safe_kwargs = _DefaultDict(kwargs)
        return self.template.format_map(safe_kwargs)

    def required_variables(self) -> list[str]:
        """Return a sorted list of placeholder names found in the template."""
        return sorted({m.group(1) for m in re.finditer(r"\{(\w+)\}", self.template)})

    def _derive_name(self) -> str:
        """Derive a short name from the first line of the template."""
        first_line = self.template.strip().split("\n")[0][:60]
        return first_line.replace(" ", "_").lower()

    def __repr__(self) -> str:
        return f"PromptTemplate(name={self.name!r}, vars={self.required_variables()})"


class _DefaultDict(dict):  # type: ignore[type-arg]
    """Dict subclass that returns empty string for missing keys.

    Used internally by ``PromptTemplate.render`` so that ``str.format_map``
    never raises ``KeyError`` for unmatched placeholders.
    """

    def __missing__(self, key: str) -> str:
        return ""
