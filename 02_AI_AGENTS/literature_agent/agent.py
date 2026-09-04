from base_agent.agent import BaseAgent


class LiteratureAgent(BaseAgent):

    def __init__(self, knowledge=None):

        super().__init__(
            "literature_agent",
            "Analyzes research papers and literature reviews",
            knowledge=knowledge
        )


    def execute(self, task):

        result = {
            "agent": self.name,
            "task": task,
            "response": "Literature analysis module activated."
        }

        if self.knowledge is not None:
            knowledge_results = self.search_knowledge(task)
            result["knowledge_results"] = knowledge_results
            result["evidence"] = [
                {
                    "chunk_id": item.get("chunk_id", item.get("id")),
                    "parent_document": item.get("metadata", {}).get(
                        "parent_document"
                    ),
                    "filename": item.get("metadata", {}).get(
                        "filename",
                        "unknown source"
                    ),
                    "excerpt": " ".join(
                        item.get("content", item.get("text", "")).split()
                    )[:300]
                }
                for item in knowledge_results
            ]

            if result["evidence"]:
                evidence_lines = [
                    (
                        f"[{evidence['filename']} | {evidence['chunk_id']}] "
                        f"{evidence['excerpt']}"
                    )
                    for evidence in result["evidence"]
                ]
                result["response"] = (
                    "Evidence retrieved from the local knowledge system:\n"
                    + "\n".join(evidence_lines)
                )
            else:
                result["response"] = (
                    "No relevant evidence was found in the local knowledge system."
                )

        return result
