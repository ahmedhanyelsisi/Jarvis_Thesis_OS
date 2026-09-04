# Stone 10 — Thesis Workspace & Document Intelligence Layer

## Purpose and boundary

Stone 10 adds deterministic inspection and confirmation-gated editing of a local
LaTeX thesis. It is an isolated `thesis_workspace` package. It does not plan,
reason, route to agents, or replace any Kernel API. The sole integration point is
the additive `Jarvis.thesis_workspace` facade owned by the Kernel.

Stones 5–9 remain unchanged in behavior. In particular, Stone 10 does not call an
agent directly and does not add a second command router. A caller reaches document
intelligence through the `Jarvis` instance, preserving the Kernel boundary.

## Architecture

The package has five responsibilities:

- `workspace_manager.py` is the facade. It coordinates discovery, parsing,
  citation checking, and safe file operations.
- `latex_parser.py` performs read-only extraction of chapters, sections and
  subsections, citations, cross-references, labels, and figures. It strips
  unescaped LaTeX comments before parsing.
- `citation_checker.py` compares citation uses with BibTeX definitions and reports
  missing, unused, and multiply defined keys with source locations.
- `file_operations.py` implements a two-stage proposal workflow. It confines paths
  to the configured root, creates a diff and content digests without writing, and
  applies only with `confirmed=True`. Atomic replacement and stale-proposal checks
  reduce partial writes and lost updates.
- `document_models.py` defines frozen models. Collections use tuples and discovery
  uses sorted POSIX-style relative paths, producing stable snapshots across runs.

## Data flow

```text
Caller
  -> Jarvis.thesis_workspace
      -> discover thesis root
          -> sorted .tex / .bib / figure paths
          -> parse each .tex file
          -> immutable ThesisStructure
      -> check_citations(ThesisStructure)
          -> parse BibTeX keys
          -> immutable CitationReport

Requested edit
  -> analyze_change / create_proposal (read only)
      -> path validation + unified diff + content digests
  -> caller reviews proposal
  -> apply(proposal, confirmed=True)
      -> stale-state validation -> atomic file replacement
```

No file is changed during discovery, parsing, checking, analysis, or proposal
creation. Omitting explicit confirmation raises `PermissionError`.

## Integration points

`Jarvis.__init__` reads the optional `thesis_workspace.root` configuration value.
Relative values are resolved from the project root; if omitted, the project root
is used. The Kernel constructs one `ThesisWorkspaceManager` and exposes it as
`Jarvis.thesis_workspace`. No existing method signature or return value is
replaced.

The public package exports the manager, parser, checker, safe operation facade,
and immutable models. This permits focused unit testing while application code
uses the Kernel-owned facade.

## Safety and deterministic behavior

- Hidden directories, `.git`, `.pytest_cache`, and `__pycache__` are excluded.
- All returned file paths are root-relative and sorted.
- File targets are resolved and must remain below the configured workspace root.
- Proposals bind the path, old state, and new content with SHA-256 digests.
- An approved proposal is rejected if the target changed since analysis.
- Writes use a temporary file in the destination directory followed by atomic
  replacement.

## Future extension path

Future stones may add a full LaTeX syntax tree, include/import graph resolution,
language-server diagnostics, bibliography style validation, figure-reference
integrity, or proposal persistence. Those extensions should implement the current
facade contracts or add new Kernel-owned adapters. They must preserve immutable
analysis results and the explicit-confirmation write boundary. No Stone 11
components are introduced here.
