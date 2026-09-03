from shared.message_protocol import AgentMessage


class BaseAgent:


    def __init__(self, name, purpose):

        self.name = name
        self.purpose = purpose


    def describe(self):

        return {
            "name": self.name,
            "purpose": self.purpose
        }


    def create_message(
        self,
        receiver,
        task
    ):

        return AgentMessage(
            sender=self.name,
            receiver=receiver,
            task=task
        )


    def execute(self, task):

        raise NotImplementedError(
            "Agent execution not implemented."
        )
