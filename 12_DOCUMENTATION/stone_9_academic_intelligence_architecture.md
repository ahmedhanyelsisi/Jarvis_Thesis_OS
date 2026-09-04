# Stone 9 — Academic Research Intelligence Layer (ARIL)

## Architecture

`Jarvis Kernel (public APIs)` → `AcademicWorkflowRouter` → `ResearchPlanner`,
`CitationStore`, `LiteratureMatrix`, and `ThesisTracker`. The four managers use
typed immutable models and deterministic in-process state. Unknown commands are
returned to the Kernel through `process_request`; no external API or second
agent/memory system is introduced.

The enforced request path is: **User → UI/Voice → Jarvis Kernel → Academic
Workflow Router → Academic Modules**. ARIL never invokes an agent, UI surface,
reasoning engine, or memory manager directly.

## Responsibilities

- **Research Planner:** converts goals and chapter requests into ordered tasks.
- **Citation Manager:** stores records, emits BibTeX, and identifies duplicates.
- **Literature Matrix:** maintains structured author/year/method/findings,
  limitations, and research-gap entries.
- **Thesis Manager:** tracks chapter sections, completion, and citation counts.
- **Academic Router:** recognizes academic commands and delegates fallback work
  through the existing Kernel interface.

## Integration flow

The Kernel constructs one router during initialization. Existing
`process_request`, `process_workflow`, and `get_system_status` contracts remain
unchanged; status gains the additive `academic_intelligence: ready` field.
Cognitive UI, voice, knowledge, memory, and reasoning components are untouched.

## Future upgrade path

Persistence can later be implemented behind the stores using the existing
memory/knowledge interfaces; citation styles, DOI validation, semantic search,
and richer workflow actions can be added without changing the model or Kernel
boundary. External retrieval and AI-assisted synthesis are intentionally out of
scope for Stone 9.

## Hardening and known limitations

Models reject empty required fields, invalid years/counts, undeclared completed
sections, unsupported citation types, and malformed citation keys. Stores return
immutable snapshots in deterministic order; missing thesis chapters and empty
matrix states are safe. Citation types are prepared for `article`, `book`,
`conference`, `thesis`, and `misc`, with no external database integration.

ARIL state remains process-local, command parsing is deliberately narrow, and
BibTeX fields are a conservative common subset. Persistence, richer citation
metadata, and broader language parsing are future extensions—not Stone 9
runtime dependencies.
