from shared.message_protocol import AgentMessage


class BaseAgent:


    def __init__(self, name, purpose, knowledge=None):

        self.name = name
        self.purpose = purpose
        self.knowledge = knowledge


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


    def search_knowledge(self, query, top_k=5):
        """Search optional shared research knowledge without coupling agents to storage."""

        if self.knowledge is None:
            return []

        return self.knowledge.search(
            query,
            top_k=top_k
        )
