import sys

sys.path.append("02_AI_AGENTS")


from diagram_agent.diagram_agent import DiagramAgent


def test_diagram_agent():

    agent = DiagramAgent()

    result = agent.execute(
        "Create research methodology framework diagram"
    )

    assert result["agent"] == "diagram_agent"


if __name__ == "__main__":

    test_diagram_agent()

    print(
        "Diagram Agent test passed."
    )
