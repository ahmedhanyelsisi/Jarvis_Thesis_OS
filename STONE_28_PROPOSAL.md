# Stone 28 Proposal — Total VS Code Intelligence Integration

**Gate:** 1 — architecture and machine capability discovery only  
**Status:** proposed; no Stone 28 implementation has started  
**Frozen baseline:** `v1.3-stone27-jarvis-hud` on `phase-2-jarvis-experience`

## 1. Executive vision

Stone 28 makes VS Code a first-class JARVIS client. Python remains the single
authoritative backend for sessions, memory, authorization, agents, retrieval,
workflows, and provider routing. The TypeScript extension collects editor
context and renders views; it is never a second JARVIS brain.

## 2. Verified machine inventory

| Surface | Verified state |
|---|---|
| Windows | Windows 11 CoreSingleLanguage, 64-bit |
| VS Code | 1.136.1, x64 |
| Node / npm | 24.19.0 / 12.0.0 |
| Git | 2.49.0.windows.1 |
| Python | 3.14.6 system interpreter; project virtual environment exists |
| JARVIS | Stone 27 commit `67d254a1201bf279b44f0af3305a0684476049d2` |

## 3. Verified VS Code environment

Installed relevant extensions: `openai.chatgpt` 26.901.22334 (Codex),
`google.google-antigravity` 1.2.0, and `james-yu.latex-workshop` 10.18.0.
Python and Pylance are also installed. VS Code's Git UX is available; a
supported programmatic Git boundary needs Gate 28I validation before mutations.

## 4. Verified Codex installation

`codex` is the official npm installation, version 0.153.0. Its CLI exposes
`exec`, `review`, `resume`, `mcp-server`, and experimental
`app-server`. `codex exec` supports working-directory selection, JSONL
output, a final-output schema, explicit model choice, ephemeral mode, and
continuation through `codex exec resume`.

## 5. Verified ChatGPT Plus authentication path

`codex login status` reports **Logged in using ChatGPT**. `codex doctor`
reports authentication mode `chatgpt`, stored ChatGPT tokens, and no stored
API key. Codex owns authentication; JARVIS must never read, copy, proxy, or
request credentials.

## 6. Explicit zero-OpenAI-API architecture

JARVIS uses the officially authenticated Codex CLI as its OpenAI reasoning
boundary. It will not introduce an OpenAI SDK, REST client, unofficial endpoint,
or credential handling.

## 7. API billing prohibition

**OPENAI API KEY REQUIRED: NO**  
**OPENAI API BILLING REQUIRED: NO**  
**OPENAI API FALLBACK: NO**  
**CHATGPT PLUS USED THROUGH: OFFICIALLY AUTHENTICATED CODEX**

No `OpenAIAPIProvider`, API-key environment entry, or call to
`api.openai.com` will be added. Limit exhaustion means local degradation,
queued work, or an explicitly chosen verified alternative—never paid fallback.

## 8. Codex Plus provider architecture

`CodexPlusReasoningProvider` will launch the verified `codex` executable
with argument arrays, an approved working directory, bounded environment and
JSONL output, timeout, and process-tree termination. Initial operations:
ANALYZE, EXPLAIN, REVIEW, DEBUG, PROPOSE_PATCH, TEST, and LATEX_REASONING.
They are analysis or proposals, never authority. The experimental app-server
and MCP-server are not required for the first provider boundary.

## 9. Codex usage-budget architecture

`CodexBudgetManager` records observable task count, elapsed time, retries,
failures, and client-visible limit evidence. It does not invent quota or scrape
account data. States: HEALTHY, CONSERVE, CRITICAL, EXHAUSTED, UNKNOWN.
EXHAUSTED blocks new Codex launches, preserves task state, and offers local
work or an explicitly selected alternative.

## 10. Runtime model-routing architecture

Use LOCAL first for retrieval, status, navigation, diagnostics, authorization,
Git reads, LaTeX health, and cached answers. Codex profiles are policy levels:
SCAN, STANDARD, DEEP, and rare FRONTIER—not hardcoded model names. Choose the
cheapest actually supported model/effort. Escalation carries compressed
evidence forward and never repeats every task across providers or models.

## 11. Antigravity inventory

Google Antigravity 1.2.0 is installed. Its declared commands cover panel focus,
snippet insertion, inline-diff accept/reject, conversation reset, and settings.
No `antigravity` CLI was found, and its manifest exposes no verified public
extension API.

## 12. Antigravity provider

`AntigravityProvider` is deferred. Gate 28G may implement it only after a
documented public API or CLI proves non-interactive use, cancellation,
working-directory control, and safe authentication ownership. No UI automation
or credential extraction is permitted.

## 13. LaTeX inventory

MiKTeX provides pdflatex, xelatex, lualatex, bibtex, biber, and latexmk.
However, latexmk currently fails because Perl is absent. Thesis root:
`D:\Masters\Thesis_Repo\Thesis_Sisi\Thesis\sisi\Templates`; root document:
`MAIN.tex`; chapters CH1–CH5 and Conclusion; bibliography `BIB_AD.bib`.
It uses biblatex configured with the BibTeX backend. No project VS Code
configuration or latexmkrc was found.

## 14. LaTeX gateway

`LaTeXWorkspaceGateway` begins with root detection and read-only log parsing.
Build, bounded clean, PDF opening, and SyncTeX are separately authorized.
Shell escape remains off. Gate 28H must resolve the Perl/latexmk readiness
issue by user-approved machine change, never silent installation.

## 15. Git environment

Git 2.49.0.windows.1 is available. The JARVIS repository is on
`phase-2-jarvis-experience`; the external thesis repository remains distinct.

## 16. Git gateway

`GitWorkspaceProvider` first offers branch, status, diff, staged, and history
reads. Stage, commit, checkout, reset, and other mutations require existing
authorization, operation preview, and trusted workspace. Auto-commit is
forbidden.

## 17. VS Code extension architecture

Create one future extension with Activity Bar container, sidebar, optional
secondary sidebar, commands, context collection, and Webview Panel. It is a
client of the Python backend.

## 18. Compact JARVIS HUD

The sidebar presents compact conversation, mission, provider, agent, health,
LaTeX, Git, and workspace state with accessible keyboard controls and explicit
error/provider labels.

## 19. Full Command Center

A Webview Panel adapts Stone 27's cosmic Core, trajectory, and agent-stone
identity to VS Code constraints. It does not blindly port the PySide HUD.

## 20. Python/TypeScript boundary

TypeScript owns VS Code integration, view state, editor context, and IPC.
Python owns reasoning, memory, agents, authorization, provider routing, thesis
intelligence, and workflows. Both UI layers are non-authoritative.

## 21. IPC decision matrix

| Transport | Strength | Limitation | Decision |
|---|---|---|---|
| JSON-RPC stdio | simple secure child ownership | no shared attach | spawn/pairing only |
| Loopback socket | familiar streaming | token/port lifecycle risk | not preferred |
| Windows named pipe | local, streaming, multi-client, native ACL | more complex | **recommended** |
| Codex app-server | official but experimental | not JARVIS IPC | do not depend on it |

## 22. IPC recommendation

Use versioned JSON-RPC 2.0 over a Windows named pipe restricted to the current
Windows user/session. Pair clients using short-lived backend-issued capability;
protect persistent local pairing material with DPAPI. Include protocol
negotiation, request/correlation IDs, payload and queue bounds, rate limits, and
disconnect cleanup. The same-interactive-user malicious-code residual threat is
documented, not claimed solved.

## 23. Single-backend strategy

Use a single-instance lock and one Python backend shared by desktop HUD and VS
Code. This prevents duplicated memory, authorization, agents, and workflows.

## 24. Attach-or-start lifecycle

VS Code reads a non-secret per-user descriptor and attempts versioned
authenticated attach. If none is compatible, it launches Python via stdio,
pairs the child, and reports ownership. Desktop-owned backends only detach from
VS Code; VS Code-owned backends stop after final client detaches and no active
authorized workflow remains.

## 25. Workspace Context Engine

`WorkspaceContextProvider` gathers workspace folders/trust, active editor,
path/language, cursor, selection, bounded surrounding text, open/dirty editors,
diagnostics, and resolvable LaTeX root/chapter.

## 26. Editor context

Context is collected on demand and correlated to the request. Dirty content is
marked as unsaved and never treated as file-on-disk truth.

## 27. Context-level/token-budget policy

| Level | Allowed context |
|---|---|
| 0 | request only |
| 1 | selection and file metadata |
| 2 | bounded local section/function |
| 3 | selected related diagnostics/files |
| 4 | retrieved thesis knowledge |
| 5 | broader project context when justified |

Full thesis and full repository transmission are forbidden by default.

## 28. Retrieval-first architecture

Resolve intent, gather local evidence, retrieve relevant thesis/code material,
compress it to the smallest sufficient context, and invoke an external provider
only if local capability is insufficient.

## 29. ReasoningBroker

`ReasoningBroker` routes among LOCAL_JARVIS, CODEX_PLUS, future verified
ANTIGRAVITY, and ACADEMIC_WORKFLOW. Local deterministic work does not consume
Codex allowance.

## 30. ProviderResult schema

ProviderResult includes provider, task ID, provider session ID when available,
model/effort only when reported, summary, findings, files referenced, proposed
changes, tests, risks, structured payload, timing, and observable usage data.

## 31. Provider routing

Providers are invoked singly by default. Comparison is explicit user intent:
invoke each, normalize results, and let a ReviewerAgent compare evidence.

## 32. Academic agent/provider separation

UI always distinguishes **provider** (LOCAL/CODEX/ANTIGRAVITY) from owning
academic agent. Providers may not grant authority, change autonomy, approve
their own work, or silently mutate anything.

## 33. Patch-first workflow

Request → analysis → proposed patch → diff preview → user approval → apply →
verify → optional authorized build → result. Silent thesis/code rewrites are
forbidden.

## 34. Approval integration

All write, build, clean, process, and Git mutation requests pass the frozen
authorization architecture. A UI proposal ID never grants authority by itself.

## 35. Workspace Trust

Untrusted workspaces allow minimal view/navigation only. Disable provider
workspace execution, writes, LaTeX build, and Git mutations until VS Code trust
is established.

## 36. Process security

External CLIs use validated executable paths/working directories, argument
arrays, minimal environment, output/result bounds, timeout, secret redaction,
and process-tree termination. No shell concatenation.

## 37. Cancellation

One task/session-correlated cancel propagates where supported to Codex, future
Antigravity, LaTeX, and workflows. Late process output cannot revive terminal
task state.

## 38. Timeouts

Every external operation has timeout, bounded stdout/stderr, result-size limit,
status/heartbeat where available, and clean termination.

## 39. Desktop HUD coexistence

Desktop PySide HUD and VS Code attach to the same backend and share sessions,
memory, authorization, agents, reasoning broker, thesis context, and workflow
state.

## 40. VS Code commands

Open Command Center; Ask/Review Selection; Review Current File/Chapter; Explain
Error; Build Thesis; Check Citations; Research Topic; Ask Codex; Ask
Antigravity; Compare Providers; Show Mission; Show Agents; Show Health; Cancel
Task.

## 41. LaTeX UX

Support root/build health, errors, citations, undefined references, chapter
navigation, PDF opening, and SyncTeX only through the authorized gateway.

## 42. Codex UX

Show actual state: LOCAL ACTIVE, CODEX THINKING, AUTHENTICATION REQUIRED,
LIMIT REACHED, or unavailable. Never show invented quota/model metadata.

## 43. Antigravity UX

Show installed-but-unverified capability honestly until Gate 28G validates a
provider boundary. Do not imply it is callable by JARVIS yet.

## 44. Provider visualization

Provider and academic-agent identity are shown independently alongside mission,
health, and approval state.

## 45. Tests

Test extension activation, protocol/version compatibility, attach/start races,
context bounds, view state, command routing, and desktop/VS Code shared state.

## 46. Security tests

Test pipe ACL/pairing, malformed/oversized/backpressured requests, untrusted
workspace restrictions, authorization denial, process argument safety, redaction,
timeout/cancel, and explicit no-API-key/no-API-network assertions.

## 47. Usage-limit behavior

**CODEX LIMIT EXHAUSTED: DEGRADE / WAIT / ALTERNATE PROVIDER.** Preserve task
state and offer local capability or explicit user-selected alternative only.

## 48. Performance

Set responsiveness, bounded-memory, no-duplicate-backend, context-latency, and
reduced-motion/accessibility gates before freeze.

## 49. Implementation gates

28A extension shell and secure IPC; 28B attach-or-start; 28C workspace/editor
context; 28D conversation; 28E CodexPlusReasoningProvider; 28F budget/routing;
28G Antigravity if verified; 28H LaTeX gateway; 28I Git/editor actions; 28J
patch/diff/approval; 28K compact HUD; 28L full integration; 28M hostile
validation, human acceptance, and freeze.

## 50. Risks

Material risks: experimental Codex app-server, absent verified Antigravity
automation boundary, same-user IPC residual threat, and latexmk blocked by
missing Perl.

## 51. Explicit deferred capabilities

Antigravity automation, full assistive-technology validation, and any feature
not backed by a documented provider surface are deferred.

## 52. User decisions required

1. Approve TypeScript client extension with Python as the one backend.
2. Approve current-user Windows named-pipe JSON-RPC, with stdio for spawn/pair.
3. Approve Codex CLI `exec --json` as initial ChatGPT-authenticated boundary.
4. Approve local-first budget routing and zero paid fallback.
5. Keep Antigravity deferred until a public interface is verified.
6. Keep LaTeX/Git read-first; builds and mutations remain authorized.
7. Approve compact sidebar plus adaptive Command Center webview.
8. Decide in Gate 28H whether to repair the Perl/latexmk prerequisite.

## 53. Final recommendation

Proceed to **28A only** after architecture approval. This creates one JARVIS
experience through shared authority/state, conserves included Codex allowance,
and keeps provider and billing boundaries honest.

**AUTOMATIC PAID FALLBACK: FORBIDDEN**
