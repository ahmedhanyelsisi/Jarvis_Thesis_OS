# Stone 11 — Academic Copilot Layer

## Purpose

Stone 11 provides deterministic thesis-level assistance above the frozen Stone 9
Academic Intelligence and Stone 10 Thesis Workspace layers. It extracts a stable
thesis context, identifies patterns in the existing literature matrix, diagnoses
academic writing, checks cross-thesis consistency, and applies a fixed
supervisor/examiner review rubric. It is an analysis layer, not an AI model or a
text-generation system.

## Architecture and boundaries

```text
Caller
  -> Jarvis Kernel
      -> Jarvis.academic_copilot (AcademicCopilot)
          -> Stone 9 public APIs
             - LiteratureMatrix.entries()
             - ThesisTracker.progress()
             - CitationStore.all()
          -> Stone 10 public API
             - ThesisWorkspaceManager.discover()
          -> immutable Stone 11 reports
```

`AcademicCopilot` is constructed by `Jarvis` from the two Kernel-owned adapters.
The package has no Kernel import and cannot construct or bypass either lower
layer. The only frozen file changed is the permitted additive integration point,
`01_CORE_KERNEL/jarvis.py`; behavior and interfaces in Stones 5–10 are unchanged.

The package responsibilities are:

- `thesis_context.py`: converts a Stone 10 snapshot and Stone 9 progress into an
  immutable `ThesisContext`, including safe empty/missing states and stable tuple
  ordering.
- `research_gap.py`: uses closed-world term frequency, explicit limitation/gap
  fields, and observed co-occurrence to return `ResearchGapReport`.
- `writing_assistant.py`: returns counts, issue codes, rubric components, and
  fixed recommendations. It never writes or completes thesis prose.
- `consistency_checker.py`: checks preferred terminology, citation-key coverage,
  declared chapter membership, and lexical research-question alignment.
- `reviewer.py`: applies fixed evidence, structure, citation, limitation, and
  minimum-depth thresholds to chapter information.
- `environment_security.py`: performs offline, read-only exact-pin comparison
  against installed distribution metadata and returns a safe `pip-audit`
  availability diagnostic.

## Supported capabilities

- Thesis context extraction from existing Stone 9 progress and Stone 10
  workspace snapshots.
- Lexical academic-gap indicators through keyword overlap, topic matching,
  term co-occurrence, and explicit gap/limitation fields.
- Missing-section indicators through controlled writing-structure templates.
- Paragraph metrics, repetition detection, missing-argument components, thesis
  consistency checks, and fixed reviewer rubric diagnostics.
- Offline detection of missing packages, exact-version mismatches, newer patch
  versions, and incompatible major versions.

## Data and determinism

All returned models are frozen dataclasses. Mutable iterables are copied into
tuples, result collections are sorted or have an explicitly stable ranking, and
every model provides a JSON-compatible `to_dict()` representation. Thesis
progress is represented as a percentage from 0 through 100 and is calculated
from completed sections when that detail exists.

Every `ResearchGapReport` declares `gap_detection_mode: "lexical"`. The gap
analyzer considers only supplied Stone 9 records. Its vocabulary comes
from normalized record terms, its dominant themes come from document frequency,
and its possible contributions come from explicit `research_gap` fields. The
writing assistant and reviewer use named rules and fixed messages; identical
inputs produce equal outputs.

## Non-goals

- Semantic novelty detection, research-contribution validation, or human-like
  literature understanding.
- Package installation, dependency resolution, environment repair, or automatic
  vulnerability remediation.
- Model inference, prose generation, web search, external advisory retrieval,
  or background execution.

Future semantic analysis belongs to a future layer and is not part of Stone 11
hardening.

## Security decisions

- No external APIs, network clients, sockets, subprocesses, shell execution, or
  model SDKs are imported or invoked.
- No API keys, credentials, secrets, or environment-variable lookup exists.
- Stone 11 performs no filesystem writes. Thesis workspace inspection occurs
  only through the Kernel-supplied Stone 10 `discover()` API. The isolated
  environment checker may read a caller-supplied `requirements.txt`; it never
  reads thesis content or exposes a general file-operation API.
- No memory store, reasoning engine, agent registry, UI, or voice component is
  imported, constructed, or called.
- Stone 11 holds only references to the Kernel-provided Stone 9/10 facades and
  stateless deterministic analyzers. It introduces no duplicate memory or agent
  subsystem.
- The layer is read-only. It does not expose Stone 10 safe-file operations and
  cannot propose or apply filesystem changes.

## Dependency audit behavior

`EnvironmentCompatibilityChecker` reads exact `==` pins and compares them with
local `importlib.metadata` records. Package names are normalized, diagnostics
are sorted, and no package manager is invoked. `EnvironmentReport` distinguishes
missing distributions, all exact-version conflicts, newer patch versions, and
incompatible major versions. Missing, empty, unreadable, or unsupported
requirements produce controlled warnings rather than startup failures.

`audit_dependencies()` checks whether the local `pip_audit` module is available.
When it is absent or discovery itself fails, it returns a frozen
`DependencyAuditReport` with `status: "unavailable"`, a reason, and
`package_changes_performed: false`. When present, it reports availability but
does not execute an online advisory lookup: external advisory retrieval would
violate Stone 11's networking boundary. Running pip-audit against an explicitly
approved offline advisory source remains an operational validation step outside
Jarvis startup.

Neither check runs during `Jarvis` construction. Audit-tool absence, malformed
metadata, or dependency drift therefore cannot prevent the Kernel or Academic
Copilot adapter from starting.

## Integration points

`Jarvis.__init__` exposes one additive `Jarvis.academic_copilot` adapter after
constructing `academic_router` and `thesis_workspace`. The adapter obtains
literature entries, thesis progress, citation keys, and workspace structure only
through those public objects. Existing `process_request`, `process_workflow`,
reasoning, memory, voice, cognitive UI, and agent behavior remain untouched.

Direct package functions remain available for isolated deterministic analysis,
but application integration is required to enter through the Kernel-owned
adapter.

## Limitations

- Analysis is lexical and rule-based; it does not establish novelty, factual
  correctness, source quality, or semantic equivalence.
- Keyword overlap and topic matching do not provide semantic novelty detection,
  research-contribution validation, or genuine literature understanding.
- No literature is searched or retrieved. A gap report describes only the
  supplied matrix and must not be presented as an exhaustive field-level gap.
- Stone 10 currently exposes no parsed thesis title or table environments, so
  those context fields remain empty unless supplied in existing workspace
  information or by the caller.
- Research-question alignment is keyword coverage, not an assessment of whether
  a question has been answered correctly.
- Reviewer thresholds are triage signals, not replacements for supervisor,
  examiner, ethics, statistical, or domain-expert judgment.
- Writing recommendations are controlled rubric messages. Stone 11 deliberately
  does not draft, rewrite, or generate thesis prose.
- `pip-audit` capability detection is not a CVE result. A vulnerability audit
  still requires installed tooling and an approved offline advisory source.
