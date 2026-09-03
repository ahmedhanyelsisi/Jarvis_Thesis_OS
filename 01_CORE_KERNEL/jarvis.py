from agent_manager import AgentManager
from task_router import TaskRouter

from sys import path
path.append("02_AI_AGENTS")

from agent_registry import load_agents


class Jarvis:

    def __init__(self):

        self.agent_manager = AgentManager()
        self.task_router = TaskRouter()

        self.register_agents()


    def register_agents(self):

        agents = load_agents()

        for agent in agents:
            self.agent_manager.register_agent(agent)


    def process_request(self, request):

        agent_name = self.task_router.route(request)

        response = self.agent_manager.execute_agent(
            agent_name,
            request
        )

        return response
