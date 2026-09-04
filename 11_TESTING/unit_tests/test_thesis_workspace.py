"""Stone 10 thesis workspace and Kernel adapter tests."""

import codecs
from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import stat

import pytest

from jarvis import Jarvis
from thesis_workspace import (
    CitationChecker,
    DocumentElement,
    LatexDocument,
    LatexParser,
    SafeFileOperations,
    SourceLocation,
    ThesisStructure,
    ThesisWorkspaceManager,
    UnsupportedEncodingError,
    WorkspaceLockError,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "figures").mkdir()
    (tmp_path / "main.tex").write_text(
        """\\chapter{Introduction}
\\label{chap:intro}
See \\autoref{fig:model} and \\cite{known,missing}.
\\begin{figure}
  \\includegraphics[width=1cm]{figures/model.png}
  \\caption{System model}
  \\label{fig:model}
\\end{figure}
""",
        encoding="utf-8",
    )
    (tmp_path / "chapters" / "methods.tex").write_text(
        "\\section{Methods}\n\\textcite{known} describes the method.\n",
        encoding="utf-8",
    )
    (tmp_path / "references.bib").write_text(
        """@article{known,
 title = {Known}
}
@book{unused,
 title = {Unused}
}
@misc{known,
 title = {Duplicate}
}
""",
        encoding="utf-8",
    )
    (tmp_path / "figures" / "model.png").write_bytes(b"not a real png")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    return tmp_path


def test_workspace_discovery_is_complete_and_deterministic(tmp_path):
    manager = ThesisWorkspaceManager(_workspace(tmp_path))
    first = manager.discover()
    second = manager.discover()

    assert first == second
    assert first.tex_files == ("chapters/methods.tex", "main.tex")
    assert first.bibliography_files == ("references.bib",)
    assert first.figure_files == ("figures/model.png",)
    assert tuple(document.path for document in first.documents) == first.tex_files


def test_latex_parser_detects_supported_constructs_and_ignores_comments():
    source = r"""% \\chapter{Hidden}
\\chapter*{Results}
\\section[Short]{Detailed Results}
\\citep[see][p. 4]{alpha, beta}
\\cref{sec:a,sec:b}
\\label{sec:a}
\\begin{figure*}
\\includegraphics{plot.pdf}
\\caption{A plot}
\\label{fig:plot}
\\end{figure*}
"""
    parsed = LatexParser().parse(source, path="chapter.tex")

    assert [item.value for item in parsed.chapters] == ["Results"]
    assert [item.value for item in parsed.sections] == ["Detailed Results"]
    assert [item.value for item in parsed.citations] == ["alpha", "beta"]
    assert [item.value for item in parsed.references] == ["sec:a", "sec:b"]
    assert [item.value for item in parsed.labels] == ["sec:a", "fig:plot"]
    assert parsed.figures[0].path == "plot.pdf"
    assert parsed.figures[0].caption == "A plot"
    assert parsed.figures[0].label == "fig:plot"


def test_citation_checker_reports_missing_unused_and_duplicate_keys(tmp_path):
    manager = ThesisWorkspaceManager(_workspace(tmp_path))
    report = manager.check_citations()

    assert [issue.key for issue in report.missing_bibliography_entries] == ["missing"]
    assert [issue.key for issue in report.unused_bibliography_entries] == ["unused"]
    assert [issue.key for issue in report.duplicate_citation_keys] == ["known"]
    assert report.unused_citations == report.unused_bibliography_entries
    assert report.is_valid is False


def test_safe_modification_requires_approval_and_rejects_stale_proposals(tmp_path):
    operations = SafeFileOperations(tmp_path)
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    proposal = operations.create_proposal("chapter.tex", "new\n")

    assert proposal.analysis.changed
    assert "-old" in proposal.analysis.diff and "+new" in proposal.analysis.diff
    with pytest.raises(PermissionError):
        operations.apply(proposal)
    assert target.read_text(encoding="utf-8") == "old\n"

    operations.apply(proposal, confirmed=True)
    assert target.read_text(encoding="utf-8") == "new\n"

    stale = operations.create_proposal("chapter.tex", "newer\n")
    target.write_text("external change\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed"):
        operations.apply(stale, confirmed=True)


def test_safe_modification_is_confined_to_workspace(tmp_path):
    operations = SafeFileOperations(tmp_path)
    with pytest.raises(ValueError, match="inside"):
        operations.create_proposal("../outside.tex", "unsafe")


def test_kernel_exposes_only_additive_workspace_adapter(tmp_path):
    _workspace(tmp_path)
    jarvis = Jarvis(
        config={
            "memory": {"enabled": False, "database_path": str(tmp_path / "memory.sqlite")},
            "knowledge": {"enabled": False},
            "voice": {"enabled": False},
            "thesis_workspace": {"root": str(tmp_path)},
        }
    )
    try:
        assert isinstance(jarvis.thesis_workspace, ThesisWorkspaceManager)
        assert jarvis.thesis_workspace.discover().tex_files == (
            "chapters/methods.tex",
            "main.tex",
        )
        assert callable(jarvis.process_request)
        assert callable(jarvis.process_workflow)
    finally:
        jarvis.close()


def test_empty_workspace_returns_stable_empty_models(tmp_path):
    manager = ThesisWorkspaceManager(tmp_path)

    first = manager.discover()
    second = manager.discover()

    assert first == second
    assert first.tex_files == ()
    assert first.bibliography_files == ()
    assert first.figure_files == ()
    assert first.documents == ()
    assert manager.check_citations(first).is_valid


def test_malformed_latex_is_reported_without_crashing():
    parsed = LatexParser().parse(
        """\\chapter{Unclosed
\\ref{}
\\label{duplicate}
\\label{duplicate}
\\begin{figure}
""",
        path="malformed.tex",
    )

    codes = {diagnostic.code for diagnostic in parsed.diagnostics}
    assert parsed.chapters == ()
    assert parsed.references == ()
    assert {
        "duplicate_label",
        "invalid_reference",
        "malformed_figure",
        "malformed_heading",
        "unbalanced_brace",
    }.issubset(codes)


def test_parser_rejects_missing_files_and_directories(tmp_path):
    parser = LatexParser()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        parser.parse_file(tmp_path / "missing.tex")
    with pytest.raises(IsADirectoryError, match="not a file"):
        parser.parse_file(tmp_path)


def test_missing_and_malformed_bibliographies_are_safe(tmp_path):
    document = LatexParser().parse(r"\cite{orphan}", path="main.tex")
    checker = CitationChecker()

    missing = checker.check((document,), ("missing.bib",), root=tmp_path)
    assert [issue.key for issue in missing.missing_bibliography_entries] == ["orphan"]
    assert missing.missing_bibliography_files == ("missing.bib",)
    assert not missing.is_valid

    malformed_path = tmp_path / "malformed.bib"
    malformed_path.write_text("@article{broken,\n title = {Unclosed}\n", encoding="utf-8")
    malformed = checker.check((document,), (malformed_path,), root=tmp_path)
    assert malformed.malformed_bibliography_entries[0].path == "malformed.bib"
    assert [issue.key for issue in malformed.missing_bibliography_entries] == ["orphan"]


def test_citations_without_any_bibliography_are_reported_missing():
    document = LatexParser().parse(r"\cite{missing,missing}", path="main.tex")
    report = CitationChecker().check((document,), ())

    assert [issue.key for issue in report.missing_bibliography_entries] == ["missing"]
    assert len(report.missing_bibliography_entries[0].locations) == 2
    assert report.duplicate_citation_keys == ()


def test_models_defensively_freeze_inputs_and_validate_paths(tmp_path):
    heading = DocumentElement("Introduction", SourceLocation("main.tex", 1))
    supplied_chapters = [heading]
    document = LatexDocument("main.tex", chapters=supplied_chapters)
    supplied_chapters.clear()

    assert document.chapters == (heading,)
    with pytest.raises(FrozenInstanceError):
        document.path = "changed.tex"
    with pytest.raises(ValueError, match="positive"):
        SourceLocation("main.tex", 0)
    with pytest.raises(ValueError, match="workspace-relative"):
        ThesisStructure(tmp_path, ("../outside.tex",), (), (), ())
    with pytest.raises(ValueError, match="workspace-relative"):
        ThesisStructure(tmp_path, ("C:/outside.tex",), (), (), ())
    with pytest.raises(ValueError, match="correspond"):
        ThesisStructure(tmp_path, (), (), (), (document,))


def test_workspace_model_detects_duplicate_labels_and_unresolved_references(tmp_path):
    parser = LatexParser()
    first = parser.parse(
        "\\label{shared}\\ref{shared}\\ref{missing}",
        path="a.tex",
    )
    second = parser.parse("\\label{shared}", path="b.tex")
    structure = ThesisStructure(
        tmp_path,
        ("b.tex", "a.tex"),
        (),
        (),
        (second, first),
    )

    assert tuple(document.path for document in structure.documents) == ("a.tex", "b.tex")
    assert [label.value for label in structure.duplicate_labels] == ["shared"]
    assert [reference.value for reference in structure.unresolved_references] == ["missing"]


def test_file_operations_reject_invalid_and_non_file_targets(tmp_path):
    operations = SafeFileOperations(tmp_path)
    directory = tmp_path / "chapter"
    directory.mkdir()

    with pytest.raises(IsADirectoryError):
        operations.create_proposal("chapter", "content")
    with pytest.raises(ValueError, match="root"):
        operations.create_proposal(".", "content")
    with pytest.raises(ValueError, match="null"):
        operations.create_proposal("bad\x00name.tex", "content")
    with pytest.raises(TypeError, match="string or Path"):
        operations.create_proposal(123, "content")


def test_forged_proposal_is_rejected_without_writing(tmp_path):
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    operations = SafeFileOperations(tmp_path)
    proposal = operations.create_proposal("chapter.tex", "new\n")
    forged = replace(proposal, proposal_id="0" * 20)

    with pytest.raises(ValueError, match="identifier"):
        operations.apply(forged, confirmed=True)
    assert target.read_text(encoding="utf-8") == "old\n"


def test_atomic_write_failure_preserves_target_and_cleans_temporary_file(tmp_path, monkeypatch):
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    operations = SafeFileOperations(tmp_path)
    proposal = operations.create_proposal("chapter.tex", "new\n")

    def fail_replace(source, destination):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr("thesis_workspace.file_operations.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        operations.apply(proposal, confirmed=True)

    assert target.read_text(encoding="utf-8") == "old\n"
    assert tuple(tmp_path.glob(".chapter.tex.*.tmp")) == ()


def test_confirmed_empty_new_file_is_created(tmp_path):
    operations = SafeFileOperations(tmp_path)
    proposal = operations.create_proposal("empty.tex", "")

    assert proposal.analysis.changed
    written = operations.apply(proposal, confirmed=True)
    assert written.is_file()
    assert written.read_text(encoding="utf-8") == ""


def test_change_during_atomic_write_is_detected_before_replace(tmp_path, monkeypatch):
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    operations = SafeFileOperations(tmp_path)
    proposal = operations.create_proposal("chapter.tex", "new\n")
    original_fsync = os.fsync
    with operations._workspace_lock():
        pass

    def mutate_after_flush(descriptor):
        original_fsync(descriptor)
        target.write_text("concurrent\n", encoding="utf-8")

    monkeypatch.setattr("thesis_workspace.file_operations.os.fsync", mutate_after_flush)
    with pytest.raises(RuntimeError, match="changed"):
        operations.apply(proposal, confirmed=True)

    assert target.read_text(encoding="utf-8") == "concurrent\n"
    assert tuple(tmp_path.glob(".chapter.tex.*.tmp")) == ()


def test_custom_macros_and_common_environments_are_diagnostic_and_safe():
    source = r"""\newcommand{\vect}[1]{\mathbf{#1}}
\section{A complex \vect{title}}
\begin{equation}\label{eq:one}x=1\end{equation}
\begin{align*}x&=y\end{align*}
\begin{algorithm}\label{alg:one}steps\end{algorithm}
\begin{theorem}Result\end{theorem}
\begin{definition}Term\end{definition}
"""
    parsed = LatexParser().parse(source, path="complex.tex")

    assert [environment.name for environment in parsed.environments] == [
        "equation",
        "align",
        "algorithm",
        "theorem",
        "definition",
    ]
    assert parsed.environments[0].label == "eq:one"
    assert any(
        diagnostic.code == "unsupported_custom_macro"
        and "vect" in diagnostic.message
        for diagnostic in parsed.diagnostics
    )
    assert any(diagnostic.code == "malformed_heading" for diagnostic in parsed.diagnostics)


def test_unsupported_environment_syntax_never_crashes():
    parsed = LatexParser().parse(
        "\\begin{equation}x=1\\end{align}\\unknownmacro{{broken}}",
        path="unsupported.tex",
    )

    assert parsed.environments == ()
    assert any(diagnostic.code == "malformed_environment" for diagnostic in parsed.diagnostics)


def test_source_encoding_validation_accepts_utf8_and_rejects_others(tmp_path):
    parser = LatexParser()
    utf8_source = tmp_path / "utf8.tex"
    utf8_source.write_bytes(codecs.BOM_UTF8 + "\\chapter{Valid}".encode("utf-8"))
    assert parser.parse_file(utf8_source).chapters[0].value == "Valid"

    utf16_source = tmp_path / "utf16.tex"
    utf16_source.write_bytes("\\chapter{Invalid}".encode("utf-16"))
    with pytest.raises(UnsupportedEncodingError, match="UTF-16 BOM") as error:
        parser.parse_file(utf16_source)
    assert error.value.code == "unsupported_encoding"

    legacy_source = tmp_path / "legacy.tex"
    legacy_source.write_bytes(b"\\section{caf\xe9}")
    with pytest.raises(UnsupportedEncodingError, match="non-UTF-8"):
        parser.parse_file(legacy_source)


def test_atomic_replacement_preserves_original_permissions(tmp_path):
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    os.chmod(target, 0o640)
    original_mode = stat.S_IMODE(target.stat().st_mode)
    operations = SafeFileOperations(tmp_path)

    operations.apply(
        operations.create_proposal("chapter.tex", "new\n"),
        confirmed=True,
    )

    assert stat.S_IMODE(target.stat().st_mode) == original_mode


def test_workspace_lock_prevents_concurrent_write_and_releases_safely(tmp_path):
    target = tmp_path / "chapter.tex"
    target.write_text("old\n", encoding="utf-8")
    holder = SafeFileOperations(tmp_path)
    contender = SafeFileOperations(tmp_path, lock_timeout=0.02)
    proposal = contender.create_proposal("chapter.tex", "new\n")

    with holder._workspace_lock():
        with pytest.raises(WorkspaceLockError, match="Timed out"):
            contender.apply(proposal, confirmed=True)

    contender.apply(proposal, confirmed=True)
    assert target.read_text(encoding="utf-8") == "new\n"

    with pytest.raises(RuntimeError, match="simulated"):
        with holder._workspace_lock():
            raise RuntimeError("simulated lock-holder failure")
    with holder._workspace_lock():
        pass


def test_pdf_discovery_requires_reference_or_figure_asset_folder(tmp_path):
    (tmp_path / "figures").mkdir()
    (tmp_path / "plots").mkdir()
    (tmp_path / "documents").mkdir()
    (tmp_path / "main.tex").write_text(
        "\\includegraphics{plots/referenced.pdf}\n",
        encoding="utf-8",
    )
    for path in (
        tmp_path / "figures" / "asset.pdf",
        tmp_path / "plots" / "referenced.pdf",
        tmp_path / "documents" / "paper.pdf",
        tmp_path / "thesis.pdf",
    ):
        path.write_bytes(b"pdf placeholder")

    structure = ThesisWorkspaceManager(tmp_path).discover()

    assert structure.figure_files == (
        "figures/asset.pdf",
        "plots/referenced.pdf",
    )
