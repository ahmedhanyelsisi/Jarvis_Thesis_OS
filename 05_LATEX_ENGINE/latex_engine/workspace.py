from pathlib import Path
from .models import BuildRequest
from .exceptions import WorkspaceNotFoundError

class WorkspaceManager:
    """Safely resolves and validates workspace boundaries."""
    
    @staticmethod
    def validate_workspace(request: BuildRequest) -> Path:
        """
        Ensures the requested target directory exists and contains the main file.
        Returns the absolute validated root path.
        """
        root = request.target_dir.resolve()
        
        if not root.exists() or not root.is_dir():
            raise WorkspaceNotFoundError(f"Target directory {root} does not exist or is not a directory.")
            
        main_file = root / request.main_file
        if not main_file.exists() or not main_file.is_file():
            raise WorkspaceNotFoundError(f"Main LaTeX file {request.main_file} not found in {root}.")
            
        return root
