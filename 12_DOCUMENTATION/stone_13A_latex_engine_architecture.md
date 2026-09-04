# Stone 13A: Latex Engine Architecture

## 1. Overview
The `latex_engine` is an isolated, sandboxed package responsible for the deterministic compilation of LaTeX documents within JARVIS THESIS OS. It strictly parses `.log` outputs for diagnostic insights and extracts artifacts without possessing any knowledge of broader AI behaviors, memory, or the kernel.

## 2. Directory Structure
```
05_LATEX_ENGINE/
    latex_engine/
        __init__.py
        models.py
        compiler.py
        log_parser.py
        workspace.py
        artifacts.py
        exceptions.py
```

## 3. Strict Boundary Enforcement
*   **Kernel Facade Maintenance:** The core `Jarvis` class in `01_CORE_KERNEL/jarvis.py` will remain unmodified. The LaTeX Engine is strictly registered and fetched via the `ServiceRegistry`.
*   **No Configuration Dependencies:** The `latex_engine` subsystem is autonomous and does not require YAML dependency injection from `bootstrap.py`.
*   **No Forbidden Imports:** Network connections (`socket`, `requests`, `urllib`), agents, UI, or Voice dependencies are strictly disallowed.

## 4. Execution Sandbox
The `LatexCompiler` executes the `pdflatex` process entirely isolated from Python logic:
*   `shell=False` is strictly enforced.
*   Only the `pdflatex` command is allowed (no arbitrary injection).
*   Execution is governed by an immutable `BuildPolicy` model, controlling:
    *   `timeout_seconds`: Prevents infinite hanging on compilation.
    *   `shell_execution_permission`: Strictly defaults to False. If overridden to True, execution raises an immediate architectural violation.
    *   `maximum_output_size`: Prevents reading abnormally large malicious or recursive log files.

## 5. Domain Models
All representations are completely immutable (`@dataclass(frozen=True)`):
*   `BuildPolicy`: Orchestration constraints.
*   `BuildRequest`: Represents the compilation target and attached policy.
*   `LatexDiagnostic`: Standardized encapsulation of LaTeX warnings and errors.
*   `CompilationArtifact`: Paths linking to resulting assets (`.pdf`, `.log`, `.aux`).
*   `BuildResult`: Final compilation report outlining success, duration, diagnostics, and artifacts.
