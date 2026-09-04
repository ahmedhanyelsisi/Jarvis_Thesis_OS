"""Construction registry for the existing Jarvis agent implementations."""

from citation_agent.citation_agent import CitationAgent
from diagram_agent.diagram_agent import DiagramAgent
from latex_agent.latex_agent import LatexAgent
from literature_agent.agent import LiteratureAgent
from reviewer_agent.reviewer_agent import ReviewerAgent
from test_agent.test_agent import TestAgent
from thesis_writer_agent.writer_agent import ThesisWriterAgent


def load_agents(knowledge=None):
    """Instantiate every implemented agent through one shared registry."""

    agents = [
        LiteratureAgent(knowledge=knowledge),
        ThesisWriterAgent(),
        LatexAgent(),
        ReviewerAgent(),
        CitationAgent(),
        DiagramAgent(),
        TestAgent(),
    ]

    for agent in agents:
        agent.knowledge = knowledge

    return agents
