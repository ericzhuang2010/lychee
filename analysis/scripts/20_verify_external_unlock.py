#!/usr/bin/env python3
"""Fail closed until the discovery freeze and external code bundle verify."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(path: Path) -> None:
    subprocess.run(["sha256sum", "-c", str(path.relative_to(ROOT))], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-manifest", required=True)
    parser.add_argument("--unlock", required=True)
    parser.add_argument("--external-manifest", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--study", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    discovery_manifest = ROOT / args.discovery_manifest
    unlock = ROOT / args.unlock
    external_manifest = ROOT / args.external_manifest
    config_path = ROOT / args.config
    for path in (discovery_manifest, unlock, external_manifest, config_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Required external firewall artifact is absent: {path}")
    verify_manifest(discovery_manifest)
    verify_manifest(external_manifest)
    config = json.loads(config_path.read_text())
    if config.get("outcomes_viewed") is not False:
        raise ValueError("External config is not marked outcome-blind")
    if args.study not in config.get("studies", {}):
        raise ValueError(f"Study is absent from frozen external config: {args.study}")

    rows = [
        {
            "artifact": "discovery_freeze_manifest",
            "path": str(discovery_manifest.relative_to(ROOT)),
            "sha256": sha256(discovery_manifest),
            "status": "PASS",
        },
        {
            "artifact": "discovery_external_unlock",
            "path": str(unlock.relative_to(ROOT)),
            "sha256": sha256(unlock),
            "status": "PASS",
        },
        {
            "artifact": "external_analysis_bundle",
            "path": str(external_manifest.relative_to(ROOT)),
            "sha256": sha256(external_manifest),
            "status": "PASS",
        },
        {
            "artifact": "external_config",
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256(config_path),
            "status": "PASS",
        },
    ]
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["artifact", "path", "sha256", "status"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output)


if __name__ == "__main__":
    main()
