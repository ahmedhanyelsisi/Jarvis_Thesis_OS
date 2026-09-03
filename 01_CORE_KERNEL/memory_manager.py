class MemoryManager:

    def __init__(self):
        self.memory = []

    def remember(self, information):
        self.memory.append(information)

    def recall(self):
        return self.memory

