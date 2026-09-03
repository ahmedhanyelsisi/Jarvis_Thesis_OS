import sys

sys.path.append("02_AI_AGENTS")

from citation_agent.citation_agent import CitationAgent


def test_citation_agent():

    agent = CitationAgent()

    result = agent.execute(
        "Check citations and bibliography"
    )

    assert result["agent"] == "citation_agent"
    assert result["response"] == (
        "Citation and bibliography workflow activated."
    )


if __name__ == "__main__":

    test_citation_agent()

    print("Citation Agent test passed.")

