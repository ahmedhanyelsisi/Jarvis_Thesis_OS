"""Deterministic, offline environment diagnostics for Stone 11."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import metadata, util
import re
from typing import Callable, Iterable, Mapping


_PINNED_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s;#]+)\s*(?:#.*)?$"
)
_NORMALIZE_NAME = re.compile(r"[-_.]+")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _package_name(value: object) -> str:
    return _NORMALIZE_NAME.sub("-", _text(value, "package name").casefold())


def _version_parts(version: str) -> tuple[int, ...] | None:
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if match is None:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _iterable(values: object, field: str) -> tuple[object, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an iterable, not a string")
    try:
        return tuple(values)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(f"{field} must be an iterable") from error


@dataclass(frozen=True, order=True)
class InstalledPackage:
    package: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "package", _package_name(self.package))
        object.__setattr__(self, "version", _text(self.version, "installed version"))

    def to_dict(self) -> dict[str, str]:
        return {"package": self.package, "version": self.version}


@dataclass(frozen=True, order=True)
class VersionDiagnostic:
    package: str
    required_version: str
    installed_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "package", _package_name(self.package))
        object.__setattr__(self, "required_version", _text(self.required_version, "required_version"))
        object.__setattr__(self, "installed_version", _text(self.installed_version, "installed_version"))

    def to_dict(self) -> dict[str, str]:
        return {
            "package": self.package,
            "required_version": self.required_version,
            "installed_version": self.installed_version,
        }


@dataclass(frozen=True)
class EnvironmentFingerprint:
    status: str
    installed_packages: tuple[InstalledPackage, ...] = ()
    missing: tuple[str, ...] = ()
    version_drift: tuple[VersionDiagnostic, ...] = ()
    newer_patch_versions: tuple[VersionDiagnostic, ...] = ()
    major_conflicts: tuple[VersionDiagnostic, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"compatible", "drift_detected"}:
            raise ValueError("status must be compatible or drift_detected")
        installed = tuple(self.installed_packages)
        if not all(isinstance(item, InstalledPackage) for item in installed):
            raise TypeError("installed_packages must contain InstalledPackage values")
        if len({item.package for item in installed}) != len(installed):
            raise ValueError("installed_packages must contain unique package names")
        object.__setattr__(self, "installed_packages", tuple(sorted(installed)))
        missing = tuple(sorted({_package_name(item) for item in self.missing}))
        object.__setattr__(self, "missing", missing)
        for field_name in ("version_drift", "newer_patch_versions", "major_conflicts"):
            diagnostics = tuple(getattr(self, field_name))
            if not all(isinstance(item, VersionDiagnostic) for item in diagnostics):
                raise TypeError(f"{field_name} must contain VersionDiagnostic values")
            object.__setattr__(self, field_name, tuple(sorted(set(diagnostics))))
        warnings = tuple(sorted({_text(item, "warning") for item in self.warnings}, key=str.casefold))
        object.__setattr__(self, "warnings", warnings)
        if (self.status == "drift_detected") != bool(missing or self.version_drift):
            raise ValueError("status must agree with dependency diagnostics")

    @property
    def fingerprint(self) -> str:
        manifest = "".join(f"{item.package}=={item.version}\n" for item in self.installed_packages)
        return hashlib.sha256(manifest.encode("utf-8")).hexdigest()

    @property
    def missing_packages(self) -> tuple[str, ...]:
        return self.missing

    @property
    def version_conflicts(self) -> tuple[VersionDiagnostic, ...]:
        return self.version_drift

    @property
    def incompatible_major_versions(self) -> tuple[VersionDiagnostic, ...]:
        return self.major_conflicts

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "fingerprint": self.fingerprint,
            "installed_packages": [item.to_dict() for item in self.installed_packages],
            "missing": list(self.missing),
            "version_drift": [item.to_dict() for item in self.version_drift],
            "newer_patch_versions": [item.to_dict() for item in self.newer_patch_versions],
            "major_conflicts": [item.to_dict() for item in self.major_conflicts],
            "warnings": list(self.warnings),
        }


EnvironmentReport = EnvironmentFingerprint


@dataclass(frozen=True, order=True)
class DependencyVulnerability:
    package: str
    installed_version: str
    vulnerability_id: str
    fixed_versions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "package", _package_name(self.package))
        object.__setattr__(self, "installed_version", _text(self.installed_version, "installed_version"))
        object.__setattr__(self, "vulnerability_id", _text(self.vulnerability_id, "vulnerability_id"))
        fixed = tuple(sorted({_text(value, "fixed version") for value in _iterable(self.fixed_versions, "fixed_versions")}))
        object.__setattr__(self, "fixed_versions", fixed)

    def to_dict(self) -> dict[str, object]:
        return {
            "package": self.package,
            "installed_version": self.installed_version,
            "vulnerability_id": self.vulnerability_id,
            "fixed_versions": list(self.fixed_versions),
        }


@dataclass(frozen=True)
class DependencyAuditReport:
    audit_status: str
    vulnerabilities: tuple[DependencyVulnerability, ...] = ()
    reason: str = ""
    tool: str = "pip-audit"
    package_changes_performed: bool = False

    def __post_init__(self) -> None:
        if self.audit_status not in {"available", "unavailable"}:
            raise ValueError("audit_status must be available or unavailable")
        vulnerabilities = tuple(self.vulnerabilities)
        if not all(isinstance(item, DependencyVulnerability) for item in vulnerabilities):
            raise TypeError("vulnerabilities must contain DependencyVulnerability values")
        object.__setattr__(self, "vulnerabilities", tuple(sorted(set(vulnerabilities))))
        object.__setattr__(self, "tool", _text(self.tool, "tool"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        if self.audit_status == "unavailable" and vulnerabilities:
            raise ValueError("an unavailable audit cannot contain vulnerabilities")
        if self.package_changes_performed is not False:
            raise ValueError("Stone 11 dependency audits must not change packages")

    @property
    def status(self) -> str:
        return self.audit_status

    def to_dict(self) -> dict[str, object]:
        return {
            "audit_status": self.audit_status,
            "vulnerabilities": [item.to_dict() for item in self.vulnerabilities],
            "reason": self.reason,
            "tool": self.tool,
            "package_changes_performed": self.package_changes_performed,
        }


class EnvironmentCompatibilityChecker:
    """Compare supplied exact pins with local metadata without filesystem I/O."""

    def check(
        self,
        requirements: str | Iterable[str] | None = None,
        *,
        installed_packages: Mapping[str, str] | None = None,
    ) -> EnvironmentFingerprint:
        lines, source_warnings = self._requirements(requirements)
        installed = self._installed_packages(installed_packages)
        installed_models = tuple(InstalledPackage(name, version) for name, version in installed.items())
        missing: list[str] = []
        drift: list[VersionDiagnostic] = []
        newer_patches: list[VersionDiagnostic] = []
        major_conflicts: list[VersionDiagnostic] = []
        warnings = list(source_warnings)

        pins: dict[str, str] = {}
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = _PINNED_REQUIREMENT.fullmatch(line)
            if match is None:
                warnings.append(f"Ignored unpinned or unsupported requirement at line {line_number}.")
                continue
            name = _package_name(match.group(1))
            required = match.group(2)
            if name in pins and pins[name] != required:
                warnings.append(f"Conflicting requirement declarations for '{name}'.")
            pins[name] = required

        if not pins:
            warnings.append("No exact package pins were available for comparison.")

        for name, required in sorted(pins.items()):
            current = installed.get(name)
            if current is None:
                missing.append(name)
                continue
            if current == required:
                continue
            diagnostic = VersionDiagnostic(name, required, current)
            drift.append(diagnostic)
            required_parts = _version_parts(required)
            current_parts = _version_parts(current)
            if required_parts is None or current_parts is None:
                warnings.append(f"Version ordering unavailable for non-numeric version of '{name}'.")
            elif current_parts[0] != required_parts[0]:
                major_conflicts.append(diagnostic)
            elif current_parts[:2] == required_parts[:2] and current_parts[2] > required_parts[2]:
                newer_patches.append(diagnostic)

        status = "drift_detected" if missing or drift else "compatible"
        return EnvironmentFingerprint(
            status,
            installed_models,
            tuple(missing),
            tuple(drift),
            tuple(newer_patches),
            tuple(major_conflicts),
            tuple(warnings),
        )

    @staticmethod
    def _requirements(requirements: str | Iterable[str] | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if requirements is None:
            return (), ("Requirements data was not supplied through the approved caller boundary.",)
        if isinstance(requirements, str):
            return tuple(requirements.splitlines()), ()
        try:
            return tuple(_text(line, "requirement line") for line in requirements), ()
        except TypeError as error:
            if str(error).startswith("requirement line"):
                raise
            raise TypeError("requirements must be text or an iterable of lines") from error

    @staticmethod
    def _installed_packages(packages: Mapping[str, str] | None) -> dict[str, str]:
        if packages is not None:
            if not isinstance(packages, Mapping):
                raise TypeError("installed_packages must be a mapping")
            return {_package_name(name): _text(version, "installed version") for name, version in packages.items()}
        installed: dict[str, str] = {}
        for distribution in metadata.distributions():
            name = distribution.metadata.get("Name")
            if name:
                installed[_package_name(name)] = distribution.version
        return installed


def audit_dependencies(
    *,
    module_finder: Callable[[str], object | None] | None = None,
    vulnerabilities: Iterable[DependencyVulnerability] = (),
) -> DependencyAuditReport:
    """Return audit capability and caller-supplied offline audit findings."""

    finder = module_finder or util.find_spec
    try:
        available = finder("pip_audit") is not None
    except Exception as error:
        return DependencyAuditReport(
            "unavailable",
            reason=f"Audit tooling lookup failed safely: {type(error).__name__}.",
        )
    if not available:
        return DependencyAuditReport(
            "unavailable",
            reason="Audit unavailable because pip-audit is not installed; no package changes performed.",
        )
    findings = _iterable(vulnerabilities, "vulnerabilities")
    if not all(isinstance(item, DependencyVulnerability) for item in findings):
        raise TypeError("vulnerabilities must contain DependencyVulnerability values")
    return DependencyAuditReport(
        "available",
        tuple(findings),
        reason=(
    "pip-audit is available; report contains only findings supplied by an approved offline advisory source."
    )

    )
def environment_fingerprint(
    requirements: str | Iterable[str] | None = None,
    *,
    installed_packages: Mapping[str, str] | None = None,
) -> EnvironmentFingerprint:
    return EnvironmentCompatibilityChecker().check(
        requirements,
        installed_packages=installed_packages,
    )


def check_environment(
    requirements: str | Iterable[str] | None = None,
    *,
    installed_packages: Mapping[str, str] | None = None,
) -> EnvironmentFingerprint:
    return environment_fingerprint(requirements, installed_packages=installed_packages)
