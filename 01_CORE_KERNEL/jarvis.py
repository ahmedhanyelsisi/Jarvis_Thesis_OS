import sys
import os


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


AI_AGENTS_PATH = os.path.join(
    PROJECT_ROOT,
    "02_AI_AGENTS"
)


sys.path.insert(
    0,
    AI_AGENTS_PATH
)


from agent_manager import AgentManager
from task_router import TaskRouter

from thesis_writer_agent.writer_agent import ThesisWriterAgent
from latex_agent.latex_agent import LatexAgent
from reviewer_agent.reviewer_agent import ReviewerAgent
from citation_agent.citation_agent import CitationAgent
from diagram_agent.diagram_agent import DiagramAgent



class Jarvis:


    def __init__(self):

        self.agent_manager = AgentManager()

        self.task_router = TaskRouter()

        self.register_agents()



    def register_agents(self):

        writer_agent = ThesisWriterAgent()

        latex_agent = LatexAgent()

        reviewer_agent = ReviewerAgent()

        citation_agent = CitationAgent()

        diagram_agent = DiagramAgent()


        self.agent_manager.register_agent(
            writer_agent
        )

        self.agent_manager.register_agent(
            latex_agent
        )

        self.agent_manager.register_agent(
            reviewer_agent
        )

        self.agent_manager.register_agent(
            citation_agent
        )

        self.agent_manager.register_agent(
            diagram_agent
        )



    def process_request(
        self,
        request
    ):

        agent_name = self.task_router.route(
            request
        )


        return self.agent_manager.send_task(
            agent_name,
            request
        )
