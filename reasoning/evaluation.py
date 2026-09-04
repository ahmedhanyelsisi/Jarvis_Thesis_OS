"""Deterministic output evaluation and bounded improvement feedback."""

from __future__ import annotations

import json
from typing import Any

from .models import EvaluationResult


class EvaluationLoop:
    """Score outputs and optionally request bounded improvements from agents."""

    def __init__(self, agent_manager: Any | None = None, quality_threshold: int = 7) -> None:
        if not 1 <= quality_threshold <= 10:
            raise ValueError("Quality threshold must be between 1 and 10.")
        self.agent_manager = agent_manager
        self.quality_threshold = quality_threshold

    def evaluate(self, output: Any, criteria: str = "") -> EvaluationResult:
        """Evaluate completeness, correctness, consistency, and formatting."""

        text = self._as_text(output)
        lowered = text.lower()
        dimensions = {
            "completeness": 9 if len(text.strip()) >= 40 else (5 if text.strip() else 1),
            "correctness": 3 if any(token in lowered for token in ("error", "failed", "exception")) else 8,
            "consistency": 4 if "contradiction" in lowered else (8 if text.strip() else 2),
            "formatting": 8 if self._is_structured(output, text) else (6 if text.strip() else 2),
        }
        issues: list[str] = []
        if dimensions["completeness"] < 7:
            issues.append("output is incomplete or lacks sufficient detail")
        if dimensions["correctness"] < 7:
            issues.append("output contains an execution error or failure marker")
        if dimensions["consistency"] < 7:
            issues.append("output may be internally inconsistent")
        if dimensions["formatting"] < 7:
            issues.append("output formatting is weak or unstructured")

        reviewer_result = self._ask_reviewer(output, criteria)
        score = round(sum(dimensions.values()) / len(dimensions))
        recommendation = "accept output" if not issues else f"Improve {issues[0]}."
        return EvaluationResult(score, issues, recommendation, dimensions, reviewer_result)

    def evaluate_and_improve(
        self,
        output: Any,
        producing_agent: str,
        original_task: str,
        max_iterations: int = 1,
    ) -> dict[str, Any]:
        """Run a bounded feedback loop using existing agent interfaces."""

        if max_iterations < 0:
            raise ValueError("max_iterations cannot be negative.")
        current = output
        evaluations: list[dict[str, Any]] = []
        attempts = 0
        while True:
            evaluation = self.evaluate(current, original_task)
            evaluations.append(evaluation.to_dict())
            if evaluation.score >= self.quality_threshold or attempts >= max_iterations:
                break
            if self.agent_manager is None:
                break
            improvement_task = (
                f"Improve the result for: {original_task}\n"
                f"Feedback: {evaluation.recommendation}\n"
                f"Current output: {self._as_text(current)}"
            )
            response = self.agent_manager.send_task(producing_agent, improvement_task)
            if isinstance(response, dict) and response.get("status") == "failed":
                break
            current = response
            attempts += 1
        return {"final_output": current, "evaluations": evaluations, "improvement_attempts": attempts}

    def _ask_reviewer(self, output: Any, criteria: str) -> Any:
        if self.agent_manager is None:
            return None
        task = f"Evaluate output for completeness, correctness, consistency, and formatting. {criteria}\n{self._as_text(output)}"
        try:
            return self.agent_manager.send_task("reviewer_agent", task)
        except Exception as error:
            return {"status": "failed", "message": str(error)}

    @staticmethod
    def _as_text(output: Any) -> str:
        if isinstance(output, str):
            return output
        return json.dumps(output, default=str, sort_keys=True)

    @staticmethod
    def _is_structured(output: Any, text: str) -> bool:
        return isinstance(output, (dict, list, tuple)) or "\n" in text or len(text) >= 80
