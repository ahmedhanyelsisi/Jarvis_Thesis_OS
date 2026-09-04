from base_agent.agent import BaseAgent


class LatexAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "latex_agent",
            "LaTeX thesis formatting assistant"
        )


    def execute(self, task):

        return {
            "agent": self.name,
            "task": task,
            "response":
                "LaTeX workflow activated."
}
