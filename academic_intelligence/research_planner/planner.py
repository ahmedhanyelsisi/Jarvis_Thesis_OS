"""Deterministic research and chapter planning."""
from __future__ import annotations

from ..models import ResearchPlan, ResearchTask


class ResearchPlanner:
    """Turn a goal into predictable, editable research work items."""

    def plan_research(self, goal: str) -> ResearchPlan:
        if not isinstance(goal, str):
            raise TypeError("Research goal must be a string")
        goal = " ".join(goal.split()).strip()
        if not goal:
            raise ValueError("Research goal must not be empty")
        tasks = (
            ResearchTask("Define research question", f"Clarify scope and success criteria for: {goal}", 1),
            ResearchTask("Review literature", f"Collect and synthesize sources relevant to: {goal}", 1),
            ResearchTask("Select methodology", "Justify the design, data, and analysis approach.", 2),
            ResearchTask("Analyze evidence", "Execute analysis and record reproducible findings.", 2),
            ResearchTask("Draft and review", "Write conclusions, limitations, and the contribution.", 3),
        )
        return ResearchPlan(goal=goal, steps=tasks)

    create_plan = plan_research

    def plan_chapter(self, chapter: int | str, title: str | None = None) -> ResearchPlan:
        if isinstance(chapter, bool):
            raise ValueError("chapter must be a positive integer")
        try:
            number = int(chapter)
        except (TypeError, ValueError) as exc:
            raise ValueError("chapter must be a positive integer") from exc
        if number < 1 or (isinstance(chapter, str) and str(number) != chapter.strip()):
            raise ValueError("chapter must be a positive integer")
        if title is not None and not isinstance(title, str):
            raise TypeError("chapter title must be a string")
        chapter_title = (title or f"Chapter {number}").strip()
        if not chapter_title:
            raise ValueError("chapter title must not be empty")
        names = ("Introduction and scope", "Literature and context", "Methodology", "Results", "Discussion and conclusion")
        tasks = tuple(ResearchTask(name, f"Prepare {name.lower()} for {chapter_title}", i + 1) for i, name in enumerate(names))
        return ResearchPlan(goal=chapter_title, steps=tasks, chapters=(chapter_title,))

    generate_chapter_plan = plan_chapter

    def research_tasks(self, goal: str) -> list[ResearchTask]:
        return list(self.plan_research(goal).steps)

    generate_task_list = research_tasks


Planner = ResearchPlanner
