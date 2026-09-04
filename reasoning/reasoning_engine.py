"""Deterministic request analysis for the Jarvis reasoning layer."""

from __future__ import annotations

from .models import ExecutionStrategy


class ReasoningEngine:
    """Classify requests and produce repeatable execution strategies."""

    _TEMPLATES: dict[str, tuple[list[str], list[str], list[str]]] = {
        "academic_writing": (
            [
                "Analyze research objectives",
                "Retrieve relevant literature",
                "Generate methodology outline",
                "Write LaTeX section",
                "Review consistency",
            ],
            ["thesis_writer_agent", "literature_agent", "latex_agent", "reviewer_agent"],
            ["academic analysis", "literature retrieval", "writing", "LaTeX", "review"],
        ),
        "literature_research": (
            ["Find relevant research papers", "Review literature findings"],
            ["literature_agent", "reviewer_agent"],
            ["literature retrieval", "evidence review"],
        ),
        "diagram_creation": (
            ["Create architecture diagram", "Review diagram consistency"],
            ["diagram_agent", "reviewer_agent"],
            ["visualization", "review"],
        ),
        "latex_formatting": (
            ["Format content in LaTeX", "Review formatting"],
            ["latex_agent", "reviewer_agent"],
            ["LaTeX", "format review"],
        ),
        "testing": (
            ["Execute requested tests", "Review test results"],
            ["test_agent", "reviewer_agent"],
            ["testing", "result review"],
        ),
        "general_writing": (
            ["Draft requested content", "Review generated content"],
            ["thesis_writer_agent", "reviewer_agent"],
            ["writing", "review"],
        ),
    }

    def analyze(self, request: str) -> ExecutionStrategy:
        """Analyze *request* without an external model or API."""

        if not isinstance(request, str) or not request.strip():
            raise ValueError("A non-empty user request is required.")

        task_type = self._classify(request.lower())
        steps, agents, capabilities = self._TEMPLATES[task_type]
        complexity = "simple" if len(steps) <= 2 else "complex"
        return ExecutionStrategy(
            task_type=task_type,
            complexity=complexity,
            steps=list(steps),
            required_agents=list(agents),
            required_capabilities=list(capabilities),
        )

    @staticmethod
    def _classify(request: str) -> str:
        if any(word in request for word in ("methodology", "thesis chapter", "write chapter")):
            return "academic_writing"
        if any(word in request for word in ("paper", "literature", "article", "study")):
            return "literature_research"
        if any(word in request for word in ("diagram", "figure", "visual", "architecture")):
            return "diagram_creation"
        if any(word in request for word in ("latex", "tex", "equation", "typeset")):
            return "latex_formatting"
        if any(word in request for word in ("test", "verify", "validation")):
            return "testing"
        return "general_writing"
