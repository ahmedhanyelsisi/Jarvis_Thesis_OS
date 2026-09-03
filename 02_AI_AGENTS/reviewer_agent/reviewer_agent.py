from base_agent.agent import BaseAgent


class ReviewerAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "reviewer_agent",
            "Academic thesis review assistant"
        )


    def execute(self, task):

        return {
            "agent": self.name,
            "task": task,
            "response":
                "Academic review workflow activated."
        }
