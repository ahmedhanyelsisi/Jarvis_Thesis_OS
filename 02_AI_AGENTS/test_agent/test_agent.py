from base_agent.agent import BaseAgent


class TestAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "test_agent",
            "Testing communication"
        )


    def execute(self, task):

        return f"Task completed: {task}"
