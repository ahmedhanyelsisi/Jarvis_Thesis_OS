import os
import sys

# We must be able to import jarvis_core to boot the rest of the system
from .exceptions import BootSequenceError
from .health_monitor import HealthMonitor
from .command_router import CommandRouter
from .interface_gateway import InterfaceGateway

class JarvisBootloader:
    """Master orchestrator for system startup."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.registry = None
        self.health_monitor = None
        self.command_router = None
        self.interface = None
        
    def boot(self):
        """Executes the 8-step boot sequence."""
        print("[BOOT] 1. Starting JARVIS boot sequence...")
        
        print("[BOOT] 2. Verifying dependencies...")
        core_path = os.path.join(self.workspace_root, "jarvis_core")
        if not os.path.exists(core_path):
            raise BootSequenceError("Critical failure: jarvis_core not found.")
            
        print("[BOOT] 3. Initializing Service Registry and Stones 1-23...")
        # Add root to path so we can import jarvis_core
        if self.workspace_root not in sys.path:
            sys.path.insert(0, self.workspace_root)
            
        from jarvis_core.bootstrap import boot_system, ServiceRegistry
        self.registry = boot_system(self.workspace_root)
        
        print("[BOOT] 4. Activating Agent Runtime...")
        # Handled inside boot_system (SystemActivator)
        
        print("[BOOT] 5. Connecting Memory and Workspace...")
        # Handled inside boot_system
        
        print("[BOOT] 6. Starting Health Monitor...")
        self.health_monitor = HealthMonitor(self.registry)
        if not self.health_monitor.is_healthy():
            print("[WARN] Some subsystems are offline. Operating in degraded mode.")
            
        print("[BOOT] 7. Initializing Command Router and Interface...")
        self.command_router = CommandRouter(self.registry)
        self.interface = InterfaceGateway()
        
        print("[BOOT] 8. System Ready.")
        
    def get_runtime_components(self):
        if not self.registry:
            raise BootSequenceError("System not booted.")
        return {
            "registry": self.registry,
            "health_monitor": self.health_monitor,
            "command_router": self.command_router,
            "interface": self.interface
        }
