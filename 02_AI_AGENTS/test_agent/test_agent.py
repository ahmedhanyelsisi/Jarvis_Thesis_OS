from base_agent.agent import BaseAgent


class TestAgent(BaseAgent):

    __test__ = False


    def __init__(self):

        super().__init__(
            "test_agent",
            "Testing communication"
        )


    def execute(self, task):

        return f"Task completed: {task}"
