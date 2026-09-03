# Jarvis Thesis OS Architecture

## 1. Vision

Jarvis Thesis OS is an AI-powered research operating system that assists researchers throughout the complete thesis lifecycle—from literature discovery and knowledge organization to writing, citation management, review, visualization, typesetting, and presentation.

The system is designed to coordinate specialized AI capabilities within a consistent research workflow while keeping the human researcher in control of objectives, evidence, and final decisions.

## 2. Core Principles

### Modular AI agents

Each agent provides a focused research capability behind a common interface. Agents can be developed, tested, configured, and replaced independently without coupling the entire system to one model or workflow.

### Human researcher remains the decision maker

Jarvis supports research judgment; it does not replace it. The researcher defines the goals, evaluates evidence, approves important changes, and remains responsible for the final scholarly output.

### Separation between AI system and thesis repository

The orchestration platform is kept separate from the thesis content it operates on. This boundary protects the portability and integrity of the research repository while allowing Jarvis Thesis OS to evolve as an independent system.

### Reusable research workflows

Common thesis activities are represented as repeatable workflows. This makes successful research processes easier to automate, validate, reuse across projects, and improve over time.

## 3. System Architecture Layers

### Core Kernel

The Core Kernel is the control plane of Jarvis Thesis OS. It receives requests, coordinates routing and agent execution, manages system configuration, and returns a unified response. It contains the Task Router, Agent Registry, and Agent Manager.

### AI Agent Layer

The AI Agent Layer contains specialized agents built on the Base Agent Framework. Each agent owns a well-defined research responsibility and can use shared system services without duplicating orchestration logic.

### Knowledge System

The Knowledge System provides persistent research context. It is intended to organize papers, notes, extracted findings, project knowledge, researcher preferences, and future long-term research memory.

### Document Engine

The Document Engine manages structured scholarly content and document-oriented workflows. Its responsibilities include drafting, revising, reviewing, and assembling thesis material while preserving a clear relationship between sources and written outputs.

### LaTeX Engine

The LaTeX Engine supports thesis typesetting and compilation workflows. It is responsible for LaTeX-aware generation, template integration, build diagnostics, formatting validation, and publication-ready output.

### Research Intelligence Engine

The Research Intelligence Engine provides capabilities for literature analysis, evidence synthesis, citation-aware reasoning, research-gap discovery, and methodological support.

### Visual Intelligence Engine

The Visual Intelligence Engine supports the creation and refinement of diagrams, figures, data visualizations, and presentation assets derived from research content.

### Interface Layer

The Interface Layer exposes Jarvis Thesis OS to the researcher. It provides the interaction boundary for current command-driven use and future chat, voice, dashboard, and Jarvis-style heads-up display experiences.

## 4. Core Kernel Execution Flow

The Core Kernel transforms a user request into a routed agent task and returns the resulting output through a consistent execution path:

```text
User Request
     ↓
Jarvis Core
     ↓
Task Router
     ↓
Agent Registry
     ↓
Agent Manager
     ↓
Specialized Agent
     ↓
Response
```

- **Jarvis Core** accepts the request and coordinates the execution lifecycle.
- **Task Router** interprets the request and selects an agent through configuration-based routing.
- **Agent Registry** resolves the selected agent to an available implementation.
- **Agent Manager** initializes and executes the agent through the common framework.
- **Specialized Agent** performs the domain-specific work and returns a structured result.

## 5. Current Implementation Status

The following foundational capabilities are complete:

- Repository architecture
- Foundation environment
- Core Kernel
- Task Router
- Configuration-based routing
- Agent Manager
- Base Agent Framework
- Agent Registry
- Literature Agent
- Kernel Testing

These components establish the execution foundation for adding more specialized agents and shared research services without redesigning the kernel.

## 6. Current and Future Agents

### Current

- **Literature Agent** — supports literature-focused research tasks through the shared agent framework and kernel execution path.

### Future

- **Thesis Writer Agent** — assists with structured drafting, revision, and chapter-level coherence.
- **LaTeX Agent** — manages LaTeX authoring, formatting, compilation, and diagnostics.
- **Citation Agent** — supports citation discovery, validation, formatting, and reference consistency.
- **Reviewer Agent** — evaluates clarity, rigor, structure, and compliance with research requirements.
- **Diagram Agent** — creates and refines research diagrams, figures, and visual explanations.
- **Presentation Agent** — transforms thesis content into clear defense and research presentations.

## 7. Development Roadmap

### Phase 1: Foundation

Establish the repository structure, development environment, project conventions, and architectural boundaries.

### Phase 2: Core Kernel

Build the central execution system, including routing, agent registration, lifecycle management, configuration, and kernel testing.

### Phase 3: Multi-Agent Intelligence

Expand the specialized agent ecosystem and introduce coordinated workflows across writing, LaTeX, citations, review, diagrams, and presentations.

### Phase 4: Research Memory

Develop persistent, source-aware research memory for papers, notes, findings, decisions, preferences, and project context.

### Phase 5: Jarvis Interface

Deliver a unified researcher experience through conversational, visual, and voice-enabled interfaces.

### Phase 6: Autonomous Research OS

Enable supervised, goal-driven research workflows that can plan and coordinate complex tasks while preserving human oversight and approval.

## 8. Development Philosophy

> The Core Kernel controls the system.
>
> Agents provide specialized intelligence.
>
> The researcher provides direction.

This division of responsibility keeps the architecture understandable, extensible, and accountable. The kernel provides reliable coordination, agents contribute focused capabilities, and the researcher remains the authority over the research process and its outcomes.
