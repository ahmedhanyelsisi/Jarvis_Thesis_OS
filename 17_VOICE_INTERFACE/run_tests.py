"""Explicitly run all three suites without touching frozen pytest configuration."""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parent / "test-results")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.results.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(PYTHONPATH=os.pathsep.join((str(root / "16_CONVERSATION_ENGINE"), str(root / "17_VOICE_INTERFACE"), str(root))),
                       HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", ANONYMIZED_TELEMETRY="False",
                       PYTHONDONTWRITEBYTECODE="1")
    failed = False
    for name, directory in (("frozen", "11_TESTING/unit_tests"), ("conversation", "16_CONVERSATION_ENGINE/tests"),
                             ("voice", "17_VOICE_INTERFACE/tests")):
        temporary = tempfile.mkdtemp(prefix=f"stone26-{name}-", dir=args.results)
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", directory, "-q", "-o", "addopts=",
                    "-p", "no:cacheprovider", "--basetemp", temporary,
                    "--junitxml", str((args.results / f"{name}.xml").resolve())], cwd=root, env=environment,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=False)
        (args.results / f"{name}.log").write_text(result.stdout, encoding="utf-8")
        print(result.stdout)
        failed = failed or result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
