class BaseAgent:

    def __init__(self, name, purpose):
        self.name = name
        self.purpose = purpose


    def describe(self):
        return {
            "name": self.name,
            "purpose": self.purpose
        }


    def execute(self, task):
        raise NotImplementedError(
            "Each agent must implement its own execution method."
        )
