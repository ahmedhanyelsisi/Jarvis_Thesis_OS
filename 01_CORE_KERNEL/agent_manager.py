class AgentManager:

    def __init__(self):
        self.agents = {}


    def register_agent(self, agent):
        self.agents[agent.name] = agent


    def list_agents(self):
        return list(self.agents.keys())


    def get_agent(self, name):
        return self.agents.get(name)


    def execute_agent(self, name, task):

        agent = self.get_agent(name)

        if agent is None:
            return {
                "error": f"Agent {name} not found."
            }

        return agent.execute(task)
