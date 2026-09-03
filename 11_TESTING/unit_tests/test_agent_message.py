import sys

sys.path.append("02_AI_AGENTS")

from shared.message_protocol import AgentMessage


def test_agent_message():

    message = AgentMessage(
        sender="literature_agent",
        receiver="writer_agent",
        task="Create introduction"
    )

    message.complete(
        "Introduction generated"
    )

    result = message.to_dict()

    assert result["status"] == "completed"


if __name__ == "__main__":

    test_agent_message()

    print(
        "Agent communication test passed."
    )
