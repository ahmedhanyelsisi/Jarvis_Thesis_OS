from typing import Optional, Dict, List
from .models import WorkflowState, WorkflowNode
from .exceptions import InfiniteLoopError

class WorkflowScheduler:
    """DAG Execution Engine that computes the next node in the workflow."""
    
    def __init__(self, max_steps: int = 50):
        self._max_steps = max_steps
        
    def get_next_node(self, state: WorkflowState) -> Optional[WorkflowNode]:
        """Determine the next node to execute based on state."""
        if state.status not in ("RUNNING", "PENDING"):
            return None
            
        if len(state.history) > self._max_steps:
            raise InfiniteLoopError(f"Workflow {state.workflow_id} exceeded {self._max_steps} steps.")
            
        if state.pending_checkpoint:
            # Cannot proceed until checkpoint is resolved
            return None
            
        if not state.current_node:
            # We need to start
            if not state.nodes:
                return None
            # Find a start node (a node with no dependencies, or simply the first inserted for now)
            # A real DAG would resolve topological sort, here we assume it's set properly or just take the first pending.
            pending = [n for n in state.nodes.values() if n.status == "PENDING"]
            if pending:
                return pending[0]
            return None
            
        # We have a current node, what's next?
        # This requires DAG definitions. For this implementation, we will rely on 
        # the orchestrator to advance the `current_node` based on the previous node's output,
        # or we just return the current_node if it's PENDING/failed and retryable.
        node = state.nodes.get(state.current_node)
        if node and node.status in ("PENDING", "FAILED"):
            if node.retry_count < node.max_retries:
                return node
                
        return None
