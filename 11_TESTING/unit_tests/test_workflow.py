import sys
import os


sys.path.append(
    os.path.join(
        os.getcwd(),
        "08_INTERFACE",
        "workflows"
    )
)


from workflow_engine import WorkflowEngine



class MockAgentManager:


    def send_task(self, agent, task):

        return {
            "agent": agent,
            "task": task,
            "status": "completed"
        }



def test_workflow():


    manager = MockAgentManager()


    workflow = WorkflowEngine(
        manager
    )


    result = workflow.run_thesis_workflow(
        "Artificial Intelligence in Education"
    )


    assert len(result) == 6

    assert result[0]["agent"] == "literature_agent"

    assert result[-1]["agent"] == "citation_agent"



if __name__ == "__main__":

    test_workflow()

    print(
        "Multi-Agent Workflow test passed."
    )
