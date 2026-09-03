import yaml


class TaskRouter:

    def __init__(self):

        with open("jarvis_config.yaml", "r") as file:
            self.config = yaml.safe_load(file)


    def route(self, task):

        task = task.lower()

        rules = self.config.get("routing", {})

        for agent, data in rules.items():

            keywords = data.get("keywords", [])

            for keyword in keywords:

                if keyword in task:
                    return agent

        return "general_agent"

