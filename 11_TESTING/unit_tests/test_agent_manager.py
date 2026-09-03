import sys

sys.path.append("01_CORE_KERNEL")
sys.path.append("02_AI_AGENTS")


from agent_manager import AgentManager
from test_agent.test_agent import TestAgent



def test_agent_manager():

    manager = AgentManager()

    agent = TestAgent()

    manager.register_agent(agent)


    result = manager.send_task(
        "test_agent",
        "Create a test response"
    )


    assert result["status"] == "completed"



if __name__ == "__main__":

    test_agent_manager()

    print(
        "Agent manager test passed."
    )
