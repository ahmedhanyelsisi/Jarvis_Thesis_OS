import sys

sys.path.append("02_AI_AGENTS")


from reviewer_agent.reviewer_agent import ReviewerAgent


def test_reviewer_agent():

    agent = ReviewerAgent()

    result = agent.execute(
        "Review thesis methodology chapter"
    )

    assert result["agent"] == "reviewer_agent"



if __name__ == "__main__":

    test_reviewer_agent()

    print(
        "Reviewer Agent test passed."
    )
