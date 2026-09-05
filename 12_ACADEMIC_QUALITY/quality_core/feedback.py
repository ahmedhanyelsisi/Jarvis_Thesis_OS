import uuid
from typing import List, Tuple
from .models import QualityScore, RevisionTask

class FeedbackGenerator:
    """Converts score shortfalls into specific RevisionTasks."""
    
    @staticmethod
    def generate_tasks(score: QualityScore, threshold: float = 7.0) -> Tuple[RevisionTask, ...]:
        tasks = []
        for metric in score.metrics:
            if metric.score < threshold:
                severity = "CRITICAL" if metric.score < 4.0 else ("HIGH" if metric.score < 6.0 else "MEDIUM")
                
                # In a real system, the description would be enriched by the LLM reasoning
                description = f"Improve {metric.name}. Score: {metric.score}/10.0. Reason: {metric.reasoning}"
                
                task = RevisionTask(
                    task_id=str(uuid.uuid4()),
                    description=description,
                    severity=severity,
                    target_metric=metric.name
                )
                tasks.append(task)
                
        return tuple(tasks)
