class WorkflowEngine:


    def __init__(self, agent_manager):

        self.agent_manager = agent_manager



    def run_thesis_workflow(self, topic):


        tasks = [

            (
                "literature_agent",
                f"Analyze literature about {topic}"
            ),

            (
                "thesis_writer_agent",
                f"Write thesis section about {topic}"
            ),

            (
                "diagram_agent",
                f"Create framework diagram for {topic}"
            ),

            (
                "latex_agent",
                "Format chapter in LaTeX"
            ),

            (
                "reviewer_agent",
                "Review generated chapter"
            ),

            (
                "citation_agent",
                "Check references and bibliography"
            )

        ]


        results = []


        for agent, task in tasks:

            result = self.agent_manager.send_task(
                agent,
                task
            )

            results.append(result)


        return results
