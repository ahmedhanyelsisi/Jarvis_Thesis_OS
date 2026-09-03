import sys

sys.path.append("02_AI_AGENTS")


from latex_agent.latex_agent import LatexAgent


def test_latex_agent():

    agent = LatexAgent()

    result = agent.execute(
        "Create thesis equation"
    )

    assert result["agent"] == "latex_agent"



if __name__ == "__main__":

    test_latex_agent()

    print(
        "LaTeX Agent test passed."
    )
