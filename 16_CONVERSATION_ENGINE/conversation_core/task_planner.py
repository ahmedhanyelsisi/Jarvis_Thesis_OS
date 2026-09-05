from typing import Dict, Any, List

class TaskPlanner:
    def __init__(self):
        # Maps tasks to required agents from Stones 1-24
        self.task_agent_mapping = {
            "improve_chapter": ["WriterAgent", "ReviewerAgent"],
            "analyze_literature": ["ResearcherAgent", "ReviewerAgent"],
            "find_papers": ["ResearcherAgent"],
            "prepare_submission": ["QualityAgent", "WriterAgent"]
        }
        
    def build_workflow(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translates structured intent into an executable workflow DAG (mocked for Stone 25).
        """
        task = intent.get("task")
        target = intent.get("target")
        
        agents = self.task_agent_mapping.get(task, [])
        
        workflow = {
            "workflow_id": f"wf_{task}_{target}",
            "task": task,
            "target": target,
            "agents": agents,
            "steps": [
                {"step": 1, "agent": agent, "action": f"execute_{task}"} for agent in agents
            ]
        }
        return workflow
