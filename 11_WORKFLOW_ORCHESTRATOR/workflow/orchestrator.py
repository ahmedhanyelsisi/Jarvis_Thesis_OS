import time
from typing import Dict, Any, Optional

from jarvis_core.interfaces import IEventBus
from academic_agents.models import AgentTask
from academic_agents.orchestrator import AcademicAgentOrchestrator
from .models import WorkflowState, WorkflowNode
from .persistence import WorkflowPersistence
from .scheduler import WorkflowScheduler
from .checkpoints import CheckpointManager, CheckpointType
from .exceptions import WorkflowStateError, CheckpointError

class WorkflowOrchestrator:
    """The central orchestrator for Academic Workflows (Stone 18)."""
    
    def __init__(
        self, 
        event_bus: IEventBus, 
        agent_orchestrator: AcademicAgentOrchestrator, 
        persistence: WorkflowPersistence,
        scheduler: Optional[WorkflowScheduler] = None
    ):
        self._event_bus = event_bus
        self._agent_orchestrator = agent_orchestrator
        self._persistence = persistence
        self._scheduler = scheduler or WorkflowScheduler()
        
    def create_workflow(self, workflow_id: str, workflow_type: str, nodes: Dict[str, WorkflowNode]) -> WorkflowState:
        state = WorkflowState(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            nodes=nodes
        )
        self._persistence.save(state)
        self._event_bus.publish("workflow.started", {"workflow_id": workflow_id})
        return state

    def request_checkpoint(self, state: WorkflowState, reason: CheckpointType, node_id: str) -> WorkflowState:
        """Pause workflow and request human approval."""
        cp = CheckpointManager.create_checkpoint(reason, requested_by=node_id)
        
        # We need a new state dict
        new_state = WorkflowState(
            workflow_id=state.workflow_id,
            workflow_type=state.workflow_type,
            status="PAUSED",
            current_node=state.current_node,
            nodes=state.nodes,
            completed_nodes=state.completed_nodes,
            pending_checkpoint=cp,
            created_at=state.created_at,
            updated_at=time.time(),
            history=state.history + (f"PAUSED_FOR_{reason.name}",)
        )
        self._persistence.save(new_state)
        self._event_bus.publish("workflow.paused", {"workflow_id": state.workflow_id, "checkpoint": cp.checkpoint_id})
        return new_state

    def resolve_checkpoint(self, workflow_id: str, checkpoint_id: str, approved: bool) -> WorkflowState:
        state = self._persistence.load(workflow_id)
        if not state or not state.pending_checkpoint or state.pending_checkpoint.checkpoint_id != checkpoint_id:
            raise CheckpointError("Invalid checkpoint resolution attempt.")
            
        status = "APPROVED" if approved else "REJECTED"
        
        new_state = WorkflowState(
            workflow_id=state.workflow_id,
            workflow_type=state.workflow_type,
            status="RUNNING" if approved else "FAILED",
            current_node=state.current_node,
            nodes=state.nodes,
            completed_nodes=state.completed_nodes,
            pending_checkpoint=None,
            created_at=state.created_at,
            updated_at=time.time(),
            history=state.history + (f"CHECKPOINT_{status}",)
        )
        self._persistence.save(new_state)
        
        if not approved:
            self._event_bus.publish("workflow.failed", {"workflow_id": workflow_id, "reason": "checkpoint_rejected"})
            
        return new_state

    def step(self, workflow_id: str) -> WorkflowState:
        """Execute one step of the workflow DAG."""
        state = self._persistence.load(workflow_id)
        if not state:
            raise WorkflowStateError(f"Workflow {workflow_id} not found.")
            
        if state.status == "PAUSED":
            return state # Waiting for checkpoint
            
        # Update status to RUNNING
        if state.status == "PENDING":
            state = self._update_state(state, status="RUNNING")

        try:
            node = self._scheduler.get_next_node(state)
        except Exception as e:
            state = self._update_state(state, status="FAILED", history=state.history + (f"FAIL: {str(e)}",))
            self._event_bus.publish("workflow.failed", {"workflow_id": workflow_id})
            return state

        if not node:
            # Nothing left to do
            state = self._update_state(state, status="COMPLETED", history=state.history + ("COMPLETED",))
            self._event_bus.publish("workflow.completed", {"workflow_id": workflow_id})
            return state

        # Execute node via Stone 17 Agent Orchestrator
        task = AgentTask(
            task_id=f"{workflow_id}_{node.node_id}",
            agent_name=node.agent_type,
            objective=node.input.get("objective", "Execute node"),
            context=node.input
        )
        
        self._event_bus.publish("agent.started", {"task_id": task.task_id})
        result = self._agent_orchestrator.dispatch_task(task)
        
        nodes = dict(state.nodes)
        
        if result.success:
            self._event_bus.publish("agent.completed", {"task_id": task.task_id})
            nodes[node.node_id] = WorkflowNode(
                node_id=node.node_id,
                agent_type=node.agent_type,
                input=node.input,
                output={"output": result.output, "metadata": result.metadata},
                status="COMPLETED",
                retry_count=node.retry_count,
                max_retries=node.max_retries,
                timeout=node.timeout
            )
            state = self._update_state(
                state, 
                nodes=nodes, 
                current_node=None, # Advance logic goes here in a real DAG
                completed_nodes=state.completed_nodes + (node.node_id,),
                history=state.history + (f"COMPLETED_{node.node_id}",)
            )
        else:
            self._event_bus.publish("agent.failed", {"task_id": task.task_id})
            new_retry = node.retry_count + 1
            if new_retry >= node.max_retries:
                status = "FAILED"
                nodes[node.node_id] = WorkflowNode(
                    node_id=node.node_id, agent_type=node.agent_type, input=node.input,
                    output={"errors": result.errors}, status="FAILED", retry_count=new_retry,
                    max_retries=node.max_retries, timeout=node.timeout
                )
                state = self._update_state(state, nodes=nodes, status="FAILED", history=state.history + (f"FAILED_{node.node_id}",))
                self._event_bus.publish("workflow.failed", {"workflow_id": workflow_id})
            else:
                nodes[node.node_id] = WorkflowNode(
                    node_id=node.node_id, agent_type=node.agent_type, input=node.input,
                    output={"errors": result.errors}, status="PENDING", retry_count=new_retry,
                    max_retries=node.max_retries, timeout=node.timeout
                )
                state = self._update_state(state, nodes=nodes, history=state.history + (f"RETRY_{node.node_id}",))
                
        return state

    def _update_state(self, old: WorkflowState, **kwargs) -> WorkflowState:
        data = {f.name: getattr(old, f.name) for f in WorkflowState.__dataclass_fields__.values()}
        data.update(kwargs)
        data["updated_at"] = time.time()
        new_state = WorkflowState(**data)
        self._persistence.save(new_state)
        return new_state
