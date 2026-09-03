import sys

sys.path.append("01_CORE_KERNEL")
sys.path.append("02_AI_AGENTS")


from thesis_writer_agent.writer_agent import ThesisWriterAgent


def test_writer_agent():

    agent = ThesisWriterAgent()

    result = agent.execute(
        "Write thesis introduction"
    )

    assert result["agent"] == "thesis_writer_agent"


if __name__ == "__main__":

    test_writer_agent()

    print(
        "Thesis Writer Agent test passed."
    )
