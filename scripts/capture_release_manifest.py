#!/usr/bin/env python3
"""Capture a no-secret, hash-addressable Phase-5 release manifest.

Run this only after API, ML and Web checks pass. The output is restricted to
the ignored evidence directory so model binaries and operational details never
enter Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(command: list[str]) -> str:
    return subprocess.check_output(["git", *command], text=True).strip()


def artifact(directory: Path, mode: str) -> dict:
    metadata_path = directory / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    files = {
        path.name: sha256(path)
        for path in sorted(directory.iterdir())
        if path.is_file()
    }
    if metadata["artifact_file"] not in files:
        raise SystemExit(f"{directory} is missing {metadata['artifact_file']}")
    declared = metadata.get("mode", "active" if metadata["model_type"] == "xgboost" else "shadow")
    if declared != mode:
        raise SystemExit(f"{directory} declares {declared}, expected {mode}")
    return {
        "mode": mode, "model_type": metadata["model_type"], "version": metadata["version"],
        "feature_schema_version": metadata["feature_schema_version"],
        "training_data_version": metadata["training_data_version"],
        "metrics": metadata["metrics"], "files_sha256": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compose-file", type=Path, default=Path("infra/docker-compose.yml"))
    parser.add_argument("--active-dir", type=Path, default=Path("ml/artifacts/current"))
    parser.add_argument("--shadow-dir", type=Path, default=Path("ml/artifacts/tcn-shadow"))
    parser.add_argument("--explanations-dir", type=Path, default=Path("ml/artifacts/explanations"))
    parser.add_argument("--knowledge-base", type=Path, default=Path("docs/knowledge-base/manifest.json"))
    parser.add_argument("--image", action="append", default=[], metavar="SERVICE=DIGEST")
    args = parser.parse_args()

    output = args.output.resolve()
    evidence_root = Path("docs/.local/phase-5").resolve()
    if not output.is_relative_to(evidence_root):
        raise SystemExit("release manifest output must stay under docs/.local/phase-5")
    if git(["status", "--porcelain"]):
        raise SystemExit("capture only from a clean Git worktree")
    explanation = args.explanations_dir / "explanation_manifest.json"
    if not explanation.is_file():
        raise SystemExit(f"missing {explanation}")
    images = {}
    for item in args.image:
        service, separator, digest = item.partition("=")
        if not separator or not service or not digest:
            raise SystemExit("--image must use SERVICE=DIGEST")
        images[service] = digest
    payload = {
        "schema_version": "oilwell-phase-5-release-v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "git_commit": git(["rev-parse", "HEAD"]),
        "compose_sha256": sha256(args.compose_file),
        "images": images,
        "active": artifact(args.active_dir, "active"),
        "shadow": artifact(args.shadow_dir, "shadow"),
        "knowledge_base": {"sha256": sha256(args.knowledge_base), "version": json.loads(args.knowledge_base.read_text(encoding="utf-8"))["version"]},
        "explanations": {"sha256": sha256(explanation), "version": json.loads(explanation.read_text(encoding="utf-8"))["version"]},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
