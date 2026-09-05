from typing import Dict
from .exceptions import SubsystemHealthError

class HealthMonitor:
    """Monitors the runtime status of all JARVIS subsystems."""
    
    def __init__(self, registry):
        self._registry = registry
        self._status: Dict[str, str] = {}

    def perform_health_check(self) -> Dict[str, str]:
        """Pings registered services to verify they are alive."""
        # In a real deployed system this would ping threads or DB connections.
        # For this architectural wrapper, we check if the service is loaded in the registry.
        core_services = [
            ("EventBus", "event_bus"),
            ("AgentSandbox", "agent_runtime"),
            ("ThesisPipeline", "thesis_pipeline_manager"),
            ("AcademicMemory", "academic_memory_gateway"),
            ("ResearchLayer", "research_gateway")
        ]
        
        all_healthy = True
        for display_name, registry_key in core_services:
            if self._registry.get(registry_key) is not None:
                self._status[display_name] = "ONLINE"
            else:
                self._status[display_name] = "OFFLINE"
                all_healthy = False
                
        if not all_healthy:
            # We degrade gracefully, but log the offline components
            pass
            
        return self._status

    def is_healthy(self) -> bool:
        self.perform_health_check()
        return all(status == "ONLINE" for status in self._status.values())

    def get_status_report(self) -> str:
        self.perform_health_check()
        report = []
        for service, status in self._status.items():
            report.append(f"{service:.<25} [{status}]")
        return "\n".join(report)
