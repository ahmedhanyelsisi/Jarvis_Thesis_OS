import re
from typing import Dict, Any
from .exceptions import CommandRouterError

class CommandRouter:
    """Safe, unintelligent intent router. Maps commands to existing Gateways."""
    
    def __init__(self, registry):
        self._registry = registry

    def route_command(self, command: str) -> Dict[str, Any]:
        """Parses the command and routes to the appropriate subsystem."""
        cmd = command.lower()
        
        # 1. Thesis Assembly / Export (Mandatory Approval Required)
        if re.search(r"\b(export|assemble|publish|compile)\b.*\bthesis\b", cmd):
            pipeline = self._registry.get("thesis_pipeline_manager")
            if not pipeline:
                raise CommandRouterError("Pipeline Manager offline.")
            # Trigger mandatory human approval via pipeline
            token = pipeline.request_human_approval("ASSEMBLING", "User requested thesis export.")
            return {
                "action": "require_approval",
                "subsystem": "ThesisPipeline",
                "message": "Thesis export requires mandatory human approval.",
                "token": token
            }
            
        # 2. Research Intelligence
        if re.search(r"\b(find|search|research)\b.*\b(papers|literature|articles)\b", cmd):
            return {
                "action": "execute_workflow",
                "subsystem": "ResearchLayer",
                "message": "Routing to ResearchAgent."
            }

        # 3. Quality Evaluation
        if re.search(r"\b(review|score|evaluate)\b.*\b(chapter|draft|methodology)\b", cmd):
            return {
                "action": "execute_workflow",
                "subsystem": "QualityLayer",
                "message": "Routing to ReviewerAgent / QualityEvaluator."
            }

        # 4. Status Check
        if re.search(r"\b(status|health|alive)\b", cmd):
            return {
                "action": "system_status",
                "subsystem": "Runtime",
                "message": "Displaying health dashboard."
            }
            
        # Default fallback
        return {
            "action": "unknown",
            "subsystem": "None",
            "message": f"I did not understand the command: '{command}'"
        }
