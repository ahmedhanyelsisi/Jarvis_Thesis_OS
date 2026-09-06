"""Verify every model asset locally before loading it. Never download at runtime."""
import hashlib
import json
import re
from pathlib import Path


class ModelAssets:
    def __init__(self, manifest):
        self.manifest = Path(manifest).resolve(strict=True)
        if self.manifest.stat().st_size > 262144:
            raise ValueError("Oversized model manifest")
        self.document = json.loads(self.manifest.read_text(encoding="utf-8"))
        if self.document.get("schema_version") != 1 or not isinstance(self.document.get("models"), dict):
            raise ValueError("Invalid model manifest")

    def resolve(self, name):
        model = self.document["models"].get(name)
        if not isinstance(model, dict) or not model.get("revision") or not model.get("license") or not model.get("release_decision"):
            raise ValueError(f"Model {name} is not provisioned with revision, license, and release metadata")
        root = (self.manifest.parent / model["path"]).resolve(strict=True)
        files = model.get("files", {})
        if not files or not isinstance(files, dict):
            raise ValueError(f"Model {name} has no verified files")
        base = root if root.is_dir() else root.parent
        checked = set()
        for relative, expected in files.items():
            candidate = (base / relative).resolve(strict=True)
            if not candidate.is_relative_to(base) or not candidate.is_file() or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("Invalid asset path/checksum")
            with candidate.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                raise ValueError(f"Model checksum mismatch: {name}/{relative}")
            checked.add(candidate)
        if root.is_file() and root not in checked:
            raise ValueError("Main model file is not verified")
        if root.is_dir():
            actual_files = {p.resolve() for p in root.rglob("*") if p.is_file()}
            if actual_files != checked:
                raise ValueError("Model directory contains unverified files")
        return root
