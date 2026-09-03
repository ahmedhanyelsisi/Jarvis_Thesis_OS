from typing import Dict


class AgentManager:


    def __init__(self):

        self.agents: Dict = {}


    def register_agent(self, agent):

        self.agents[agent.name] = agent


    def get_agent(self, name):

        return self.agents.get(name)


    def list_agents(self):

        return list(self.agents.keys())


    def send_task(
        self,
        agent_name,
        task
    ):

        agent = self.get_agent(agent_name)

        if agent is None:

            return {
                "status": "failed",
                "message": f"Agent {agent_name} not found"
            }


        result = agent.execute(task)


        return {
            "status": "completed",
            "agent": agent_name,
            "result": result
        }
