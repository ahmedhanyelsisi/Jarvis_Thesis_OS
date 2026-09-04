# Stone 5: Reasoning and Orchestration Architecture

## Purpose

Stone 5 adds deterministic reasoning and workflow coordination above the existing
Jarvis kernel and agent framework. It does not replace the Stone 1-4 execution
path: `Jarvis.process_request()` continues to route one request to one agent.
Complex work can opt into the additive `Jarvis.process_workflow()` path.

## Architecture

```text
User Request
     |
     v
Reasoning Engine
     |
     +-------------------+
     |                   |
     v                   v
Task Planner       Agent Router
     |                   |
     +---------+---------+
               |
               v
     Workflow Orchestrator
               |
      +--------+--------+
      |        |        |
      v        v        v
 Literature  LaTeX   Diagram     (existing registered agents)
      |        |        |
      +--------+--------+
               |
               v
      Review / Evaluation Loop
               |
               v
          Final Response
```

## Components

### Reasoning Engine

`reasoning.reasoning_engine.ReasoningEngine` classifies a non-empty request,
estimates complexity, identifies capabilities, and selects a repeatable strategy.
Its ordered rules and templates are local and deterministic; it has no model or
external API dependency.

### Task Planner

`reasoning.task_planner.TaskPlanner` converts strategy steps into `PlannedTask`
objects. Each task contains an id, description, registered agent name,
dependencies, result, and one of these states:

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `SKIPPED`

The current plans form a sequential chain. Dependencies are represented as a
graph so independent branches can be scheduled concurrently in a future stone.

### Agent Router

`reasoning.agent_router.AgentRouter` applies ordered capability rules and checks
the existing `AgentManager` registry before returning an agent. The requested
`writer_agent` capability resolves to the already implemented
`thesis_writer_agent`; Stone 5 does not duplicate or replace agents.

### Workflow Orchestrator

`reasoning.orchestrator.WorkflowOrchestrator` executes ready tasks through the
existing `AgentManager.send_task(agent_name, task)` interface. Dependency output
is included in the next task payload. Agent exceptions and failed responses are
captured in `WorkflowState`, and dependent work is marked `SKIPPED`.

The kernel injects the configured Stone 4 `KnowledgeManager` into the existing
agents. Literature tasks call `KnowledgeManager.search()` and return ranked
knowledge results plus source-labelled evidence before downstream writing.

`WorkflowState` tracks:

- workflow id and current task
- completed, failed, and skipped task ids
- task outputs keyed by task id

### Reasoning Memory

`reasoning.memory.ReasoningMemory` stores decisions and experience as JSON:

- previous workflow snapshots
- successful strategies and agent selections
- explicit user preferences
- compact execution history

The default `.jarvis/reasoning_memory.json` location is separate from the
Stone 4 knowledge store. The former contains orchestration experience; the
latter remains responsible for research information and evidence.

### Evaluation Loop

`reasoning.evaluation.EvaluationLoop` deterministically scores completeness,
correctness, consistency, and formatting from 1 to 10. It asks the existing
reviewer agent for an assessment when a manager is supplied and produces issues
plus an actionable recommendation. `evaluate_and_improve()` can send bounded
feedback to the producing agent and re-evaluate its result.

## Example Workflow

For `Write methodology chapter for my thesis`, the reasoning engine produces an
academic-writing strategy. The planner creates the following chain:

```text
Analyze objectives (thesis_writer_agent)
  -> Retrieve literature (literature_agent)
  -> Generate outline (thesis_writer_agent)
  -> Write LaTeX section (latex_agent)
  -> Review consistency (reviewer_agent)
```

The orchestrator records every transition and passes each dependency result to
the next task. The reviewer receives the produced artifact, and any required
improvement is sent back to that artifact's producing agent. `final_response`
therefore remains the produced or improved artifact rather than reviewer-only
feedback. The complete state and strategy are written to reasoning memory.

## Compatibility

- Existing agent names, `BaseAgent.execute()`, `AgentManager.send_task()`, and
  `AgentMessage` remain unchanged.
- The original kernel single-agent flow remains available.
- All agents are instantiated centrally by the existing agent registry.
- Stone 5 uses standard-library code only and adds no external service.

## Configuration

`jarvis_config.yaml` controls deterministic reasoning, sequential planning, the
reasoning-memory path, knowledge-system construction, evaluation enablement,
quality threshold, and bounded improvement count. Disabled reasoning or planning
prevents workflow execution; disabled evaluation preserves the produced artifact
without running the evaluation loop.

## Future Extension Points

- A parallel scheduler can execute multiple ready graph nodes.
- More deterministic strategy templates can be registered by domain.
- A richer reviewer implementation can return dimension scores while retaining
  the current evaluation contract.
- Reasoning memory can gain strategy ranking and retention policies.
- Human approval gates can be inserted before high-impact tasks.

These are extension points only; they are not Stone 6 implementations.
