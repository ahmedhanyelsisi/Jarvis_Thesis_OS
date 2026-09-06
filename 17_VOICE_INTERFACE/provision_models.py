"""Explicit online setup. Runtime providers never invoke this module."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=path.name + ".", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _commit_staged_assets(destination, stage):
    """Replace assets and manifest together, restoring the old pair on failure."""
    live_models, live_manifest = destination / "models", destination / "model_manifest.json"
    stage_models, stage_manifest = stage / "models", stage / "model_manifest.json"
    if not stage_models.is_dir() or not stage_manifest.is_file():
        raise ValueError("Provisioning stage is incomplete")
    backup = Path(tempfile.mkdtemp(prefix=".models-backup-", dir=destination))
    old_models, old_manifest = backup / "models", backup / "model_manifest.json"
    moved_models = moved_manifest = False
    try:
        if live_models.exists():
            os.replace(live_models, old_models)
            moved_models = True
        if live_manifest.exists():
            os.replace(live_manifest, old_manifest)
            moved_manifest = True
        os.replace(stage_models, live_models)
        os.replace(stage_manifest, live_manifest)
    except Exception:
        if live_models.exists() and moved_models:
            shutil.rmtree(live_models, ignore_errors=True)
        if live_manifest.exists() and moved_manifest:
            live_manifest.unlink()
        if moved_models and old_models.exists():
            os.replace(old_models, live_models)
        if moved_manifest and old_manifest.exists():
            os.replace(old_manifest, live_manifest)
        raise
    finally:
        shutil.rmtree(backup, ignore_errors=True)


def provision(destination):
    from huggingface_hub import HfApi, hf_hub_download
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".provision-", dir=destination))
    model_root = stage / "models"
    model_root.mkdir(exist_ok=True)
    cache = stage / ".download-cache"
    manifest = {"schema_version": 1, "status": "provisioned_not_hardware_validated",
                "release_decision": "download-on-first-run-or-user-supplied-verified-assets; no-bundle", "models": {}}
    api = HfApi()
    sources = (("whisper", "Systran/faster-whisper-base", None, "MIT"),
               ("piper", "rhasspy/piper-voices", "en/en_GB/alan/medium/", "See bundled MODEL_CARD; engine GPL-3.0"))
    for name, repository, prefix, license_name in sources:
        info = api.model_info(repository)
        revision = info.sha
        if name == "whisper":
            filenames = [item.rfilename for item in info.siblings
                         if item.rfilename in ("config.json", "model.bin", "tokenizer.json", "vocabulary.json", "vocabulary.txt", "preprocessor_config.json")]
        else:
            filenames = [prefix + item for item in ("en_GB-alan-medium.onnx", "en_GB-alan-medium.onnx.json", "MODEL_CARD")]
        folder = model_root / name
        folder.mkdir(exist_ok=True)
        checksums = {}
        for filename in filenames:
            print(f"Provisioning {name}: {filename} at {revision}", flush=True)
            downloaded = Path(hf_hub_download(repository, filename, revision=revision, cache_dir=cache))
            target = folder / Path(filename).name
            shutil.copyfile(downloaded, target)
            checksums[target.name] = digest(target)
        path = folder if name == "whisper" else folder / "en_GB-alan-medium.onnx"
        decision = "eligible only as a verified download or user-supplied asset" if name == "whisper" else "not bundled pending release-specific license review"
        manifest["models"][name] = {"path": path.relative_to(stage).as_posix(), "revision": revision,
                                    "source": f"https://huggingface.co/{repository}/tree/{revision}",
                                    "license": license_name, "release_decision": decision, "files": checksums}
    for name, filename in (("wake", "hey_jarvis_v0.1.onnx"), ("melspectrogram", "melspectrogram.onnx"),
                           ("embedding", "embedding_model.onnx")):
        folder = model_root / "wake"
        folder.mkdir(exist_ok=True)
        url = f"https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{filename}"
        target = folder / filename
        print(f"Provisioning {url}", flush=True)
        with urllib.request.urlopen(url, timeout=60) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
        manifest["models"][name] = {"path": target.relative_to(stage).as_posix(), "revision": "v0.5.1",
                                    "source": url, "license": "CC-BY-NC-SA-4.0 (upstream pretrained model terms)", "release_decision": "not bundled",
                                    "files": {filename: digest(target)}}
    try:
        _atomic_write(stage / "model_manifest.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        from jarvis_voice.assets import ModelAssets
        verified = ModelAssets(stage / "model_manifest.json")
        for name in manifest["models"]:
            verified.resolve(name)
        _commit_staged_assets(destination, stage)
        return manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the explicitly selected local speech assets")
    parser.add_argument("--destination", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--download", action="store_true", required=True)
    args = parser.parse_args()
    provision(args.destination)
