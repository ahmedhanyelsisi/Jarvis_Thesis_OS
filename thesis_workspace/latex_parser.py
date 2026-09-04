"""Small, dependency-free LaTeX structure parser for workspace inspection."""

from __future__ import annotations

import re
from pathlib import Path

from .document_models import (
    DocumentElement,
    FigureElement,
    LatexEnvironment,
    LatexDocument,
    ParseDiagnostic,
    SourceLocation,
)


_COMMAND = re.compile(
    r"\\(?P<command>chapter|section|subsection|subsubsection)\*?\s*"
    r"(?:\[[^\]]*\]\s*)?\{(?P<value>[^{}]*)\}"
)
_CITATION = re.compile(
    r"\\(?:cite|citep|citet|citealp|citeauthor|citeyear|parencite|textcite|autocite)\*?"
    r"(?:\s*\[[^\]]*\]){0,2}\s*\{(?P<keys>[^{}]*)\}"
)
_REFERENCE = re.compile(r"\\(?:ref|pageref|autoref|eqref|cref|Cref)\*?\s*\{(?P<keys>[^{}]*)\}")
_LABEL = re.compile(r"\\label\s*\{(?P<keys>[^{}]*)\}")
_INCLUDE_GRAPHICS = re.compile(
    r"\\includegraphics\*?(?:\s*\[[^\]]*\])?\s*\{(?P<path>[^{}]+)\}"
)
_FIGURE_ENVIRONMENT = re.compile(
    r"\\begin\s*\{figure\*?\}(?P<body>.*?)\\end\s*\{figure\*?\}",
    re.DOTALL,
)
_CAPTION = re.compile(r"\\caption(?:\s*\[[^\]]*\])?\s*\{(?P<value>[^{}]*)\}")
_HEADING_START = re.compile(r"\\(?:chapter|section|subsection|subsubsection)\*?")
_CITATION_START = re.compile(
    r"\\(?:cite|citep|citet|citealp|citeauthor|citeyear|parencite|textcite|autocite)\*?"
)
_REFERENCE_START = re.compile(r"\\(?:ref|pageref|autoref|eqref|cref|Cref)\*?")
_LABEL_START = re.compile(r"\\label\b")
_FIGURE_START = re.compile(r"\\begin\s*\{figure\*?\}")
_FIGURE_END = re.compile(r"\\end\s*\{figure\*?\}")
_COMMON_ENVIRONMENT = re.compile(
    r"\\begin\s*\{(?P<name>equation\*?|align\*?|algorithm\*?|theorem\*?|definition\*?)\}"
    r"(?P<body>.*?)\\end\s*\{(?P=name)\}",
    re.DOTALL,
)
_COMMON_ENVIRONMENT_START = re.compile(
    r"\\begin\s*\{(?P<name>equation\*?|align\*?|algorithm\*?|theorem\*?|definition\*?)\}"
)
_COMMON_ENVIRONMENT_END = re.compile(
    r"\\end\s*\{(?P<name>equation\*?|align\*?|algorithm\*?|theorem\*?|definition\*?)\}"
)
_CUSTOM_MACRO = re.compile(
    r"\\(?:(?:new|renew|provide)command\*?\s*\{?\s*\\(?P<command>[A-Za-z@]+)"
    r"|def\s*\\(?P<definition>[A-Za-z@]+))"
)


class UnsupportedEncodingError(UnicodeError):
    """Raised when a source file is not valid UTF-8 text."""

    code = "unsupported_encoding"

    def __init__(self, path: Path, detected: str) -> None:
        self.path = path
        self.detected = detected
        super().__init__(
            f"Unsupported source encoding for {path}: {detected}; UTF-8 is required."
        )


class LatexParser:
    """Extract structural LaTeX constructs without modifying source text."""

    def parse_file(self, path: str | Path, *, display_path: str | None = None) -> LatexDocument:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"LaTeX source does not exist: {source}")
        if not source.is_file():
            raise IsADirectoryError(f"LaTeX source is not a file: {source}")
        data = source.read_bytes()
        encoding = self.detect_encoding(data, path=source)
        text = data.decode(encoding, errors="strict")
        return self.parse(text, path=display_path or source.as_posix())

    @staticmethod
    def detect_encoding(data: bytes, *, path: str | Path = "<memory>") -> str:
        """Return the supported UTF-8 codec or reject a detectable alternative."""

        if not isinstance(data, bytes):
            raise TypeError("Source data must be bytes.")
        source = Path(path)
        if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
            raise UnsupportedEncodingError(source, "UTF-32 BOM")
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            raise UnsupportedEncodingError(source, "UTF-16 BOM")
        if b"\x00" in data:
            raise UnsupportedEncodingError(source, "NUL-containing or UTF-16/32 data")
        encoding = "utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8"
        try:
            data.decode(encoding, errors="strict")
        except UnicodeDecodeError as error:
            raise UnsupportedEncodingError(source, "non-UTF-8 byte sequence") from error
        return encoding

    def parse(self, text: str, *, path: str = "<memory>") -> LatexDocument:
        if not isinstance(text, str):
            raise TypeError("LaTeX source must be a string.")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("The LaTeX display path cannot be empty.")

        cleaned = self._strip_comments(text)
        diagnostics = self._syntax_diagnostics(cleaned, path)
        headings = list(_COMMAND.finditer(cleaned))
        chapters: list[DocumentElement] = []
        sections: list[DocumentElement] = []
        for match in headings:
            value = match.group("value").strip()
            if not value:
                diagnostics.append(
                    ParseDiagnostic(
                        "invalid_heading",
                        "Chapter and section titles cannot be empty.",
                        self._location(path, cleaned, match.start()),
                    )
                )
                continue
            element = self._element(value, path, cleaned, match.start())
            if match.group("command") == "chapter":
                chapters.append(element)
            else:
                sections.append(element)

        citations = self._key_elements(
            _CITATION, cleaned, path, diagnostics, invalid_code="invalid_citation"
        )
        references = self._key_elements(
            _REFERENCE, cleaned, path, diagnostics, invalid_code="invalid_reference"
        )
        labels = self._key_elements(
            _LABEL, cleaned, path, diagnostics, invalid_code="invalid_label"
        )
        seen_labels: set[str] = set()
        for label in labels:
            if label.value in seen_labels:
                diagnostics.append(
                    ParseDiagnostic(
                        "duplicate_label",
                        f"Duplicate label: {label.value}",
                        label.location,
                    )
                )
            seen_labels.add(label.value)
        figures = self._figures(cleaned, path, diagnostics)
        environments = self._environments(cleaned, path)

        return LatexDocument(
            path=path,
            chapters=tuple(chapters),
            sections=tuple(sections),
            citations=citations,
            references=references,
            labels=labels,
            figures=figures,
            environments=environments,
            diagnostics=tuple(diagnostics),
        )

    @staticmethod
    def _strip_comments(text: str) -> str:
        """Remove unescaped comments while preserving newlines and offsets."""

        lines: list[str] = []
        for line in text.splitlines(keepends=True):
            comment_at = None
            for index, character in enumerate(line):
                if character != "%":
                    continue
                backslashes = 0
                cursor = index - 1
                while cursor >= 0 and line[cursor] == "\\":
                    backslashes += 1
                    cursor -= 1
                if backslashes % 2 == 0:
                    comment_at = index
                    break
            if comment_at is None:
                lines.append(line)
            else:
                suffix = "\n" if line.endswith("\n") else ""
                lines.append(line[:comment_at] + (" " * (len(line) - comment_at - len(suffix))) + suffix)
        return "".join(lines)

    def _key_elements(
        self,
        pattern: re.Pattern[str],
        text: str,
        path: str,
        diagnostics: list[ParseDiagnostic],
        *,
        invalid_code: str,
    ) -> tuple[DocumentElement, ...]:
        elements: list[DocumentElement] = []
        for match in pattern.finditer(text):
            for key in match.group("keys").split(","):
                normalized = key.strip()
                if normalized:
                    elements.append(self._element(normalized, path, text, match.start()))
                else:
                    diagnostics.append(
                        ParseDiagnostic(
                            invalid_code,
                            "Empty key in LaTeX command.",
                            self._location(path, text, match.start()),
                        )
                    )
        return tuple(elements)

    def _syntax_diagnostics(self, text: str, path: str) -> list[ParseDiagnostic]:
        diagnostics = self._brace_diagnostics(text, path)
        command_pairs = (
            (_HEADING_START, _COMMAND, "malformed_heading"),
            (_CITATION_START, _CITATION, "malformed_citation"),
            (_REFERENCE_START, _REFERENCE, "malformed_reference"),
            (_LABEL_START, _LABEL, "malformed_label"),
        )
        for starts, complete, code in command_pairs:
            valid_starts = {match.start() for match in complete.finditer(text)}
            for start in starts.finditer(text):
                if start.start() not in valid_starts:
                    diagnostics.append(
                        ParseDiagnostic(
                            code,
                            "Malformed or incomplete LaTeX command.",
                            self._location(path, text, start.start()),
                        )
                    )

        figure_starts = tuple(_FIGURE_START.finditer(text))
        figure_ends = tuple(_FIGURE_END.finditer(text))
        if len(figure_starts) != len(figure_ends):
            unmatched = figure_starts[-1] if len(figure_starts) > len(figure_ends) else figure_ends[-1]
            diagnostics.append(
                ParseDiagnostic(
                    "malformed_figure",
                    "Unmatched figure environment boundary.",
                    self._location(path, text, unmatched.start()),
                )
            )
        complete_environments = {
            match.start() for match in _COMMON_ENVIRONMENT.finditer(text)
        }
        for start in _COMMON_ENVIRONMENT_START.finditer(text):
            if start.start() not in complete_environments:
                diagnostics.append(
                    ParseDiagnostic(
                        "malformed_environment",
                        f"Unmatched {start.group('name')} environment.",
                        self._location(path, text, start.start()),
                    )
                )
        complete_environment_ends = {
            match.start() + match.group(0).rfind("\\end")
            for match in _COMMON_ENVIRONMENT.finditer(text)
        }
        for end in _COMMON_ENVIRONMENT_END.finditer(text):
            if end.start() not in complete_environment_ends:
                diagnostics.append(
                    ParseDiagnostic(
                        "malformed_environment",
                        f"Unmatched {end.group('name')} environment.",
                        self._location(path, text, end.start()),
                    )
                )
        for macro in _CUSTOM_MACRO.finditer(text):
            name = macro.group("command") or macro.group("definition")
            diagnostics.append(
                ParseDiagnostic(
                    "unsupported_custom_macro",
                    f"Custom macro \\{name} is preserved but not interpreted.",
                    self._location(path, text, macro.start()),
                )
            )
        return diagnostics

    def _brace_diagnostics(self, text: str, path: str) -> list[ParseDiagnostic]:
        stack: list[int] = []
        diagnostics: list[ParseDiagnostic] = []
        for offset, character in enumerate(text):
            if character not in "{}" or self._is_escaped(text, offset):
                continue
            if character == "{":
                stack.append(offset)
            elif stack:
                stack.pop()
            else:
                diagnostics.append(
                    ParseDiagnostic(
                        "unbalanced_brace",
                        "Closing brace has no matching opening brace.",
                        self._location(path, text, offset),
                    )
                )
        for offset in stack:
            diagnostics.append(
                ParseDiagnostic(
                    "unbalanced_brace",
                    "Opening brace has no matching closing brace.",
                    self._location(path, text, offset),
                )
            )
        return diagnostics

    @staticmethod
    def _is_escaped(text: str, offset: int) -> bool:
        backslashes = 0
        cursor = offset - 1
        while cursor >= 0 and text[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        return backslashes % 2 == 1

    def _figures(
        self,
        text: str,
        path: str,
        diagnostics: list[ParseDiagnostic],
    ) -> tuple[FigureElement, ...]:
        figures: list[FigureElement] = []
        covered_graphics: set[int] = set()
        for environment in _FIGURE_ENVIRONMENT.finditer(text):
            body = environment.group("body")
            graphic = _INCLUDE_GRAPHICS.search(body)
            caption = _CAPTION.search(body)
            label = _LABEL.search(body)
            if graphic is not None:
                covered_graphics.add(environment.start("body") + graphic.start())
                if self._optional_value(graphic, "path") is None:
                    diagnostics.append(
                        ParseDiagnostic(
                            "invalid_figure",
                            "Included graphic path cannot be empty.",
                            self._location(path, text, environment.start("body") + graphic.start()),
                        )
                    )
            figures.append(
                FigureElement(
                    path=self._optional_value(graphic, "path"),
                    caption=self._optional_value(caption, "value"),
                    label=self._optional_value(label, "keys"),
                    location=self._location(path, text, environment.start()),
                )
            )
        for graphic in _INCLUDE_GRAPHICS.finditer(text):
            if graphic.start() not in covered_graphics:
                graphic_path = self._optional_value(graphic, "path")
                if graphic_path is None:
                    diagnostics.append(
                        ParseDiagnostic(
                            "invalid_figure",
                            "Included graphic path cannot be empty.",
                            self._location(path, text, graphic.start()),
                        )
                    )
                    continue
                figures.append(
                    FigureElement(
                        path=graphic_path,
                        caption=None,
                        label=None,
                        location=self._location(path, text, graphic.start()),
                    )
                )
        return tuple(sorted(figures, key=lambda item: (item.location.line, item.path or "")))

    def _environments(self, text: str, path: str) -> tuple[LatexEnvironment, ...]:
        environments: list[LatexEnvironment] = []
        for match in _COMMON_ENVIRONMENT.finditer(text):
            label = _LABEL.search(match.group("body"))
            environments.append(
                LatexEnvironment(
                    name=match.group("name").rstrip("*"),
                    label=self._optional_value(label, "keys"),
                    location=self._location(path, text, match.start()),
                )
            )
        return tuple(environments)

    @staticmethod
    def _optional_value(match: re.Match[str] | None, group: str) -> str | None:
        if match is None:
            return None
        value = match.group(group).strip()
        return value or None

    def _element(self, value: str, path: str, text: str, offset: int) -> DocumentElement:
        return DocumentElement(value.strip(), self._location(path, text, offset))

    @staticmethod
    def _location(path: str, text: str, offset: int) -> SourceLocation:
        return SourceLocation(path=path, line=text.count("\n", 0, offset) + 1)
