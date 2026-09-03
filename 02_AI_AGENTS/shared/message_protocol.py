from datetime import datetime


class AgentMessage:

    def __init__(
        self,
        sender,
        receiver,
        task,
        content=None,
        status="created"
    ):

        self.sender = sender
        self.receiver = receiver
        self.task = task
        self.content = content
        self.status = status
        self.timestamp = datetime.now()


    def to_dict(self):

        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "task": self.task,
            "content": self.content,
            "status": self.status,
            "timestamp": str(self.timestamp)
        }


    def complete(self, result):

        self.content = result
        self.status = "completed"


    def fail(self, error):

        self.content = error
        self.status = "failed"
