#!/usr/bin/env python3
"""Validate and freeze the accession-aware published-evidence registry."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


REQUIRED = [
    "DOI", "gene_or_pathway", "species_or_cultivar", "biological_material",
    "accession_overlap", "evidence_modality", "independent_of_current_datasets",
    "exact_support", "limitation",
]
CURRENT = {"GSE201243", "PRJNA830488", "PRJNA450886", "GSE222650", "GSE222651",
           "PRJNA922965", "PRJNA922966", "GSE262200", "PRJNA1090613"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    with args.registry.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [field for field in REQUIRED if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"published registry missing fields: {missing}")
        records = list(reader)
    if not records:
        raise ValueError("published evidence registry is empty")
    allowed = {"true", "false", "unresolved"}
    for index, row in enumerate(records, start=2):
        if any(not row[field].strip() for field in REQUIRED):
            raise ValueError(f"empty required published-evidence field on line {index}")
        independent = row["independent_of_current_datasets"].lower()
        if independent not in allowed:
            raise ValueError(f"invalid independence label on line {index}: {independent}")
        overlap = row["accession_overlap"].upper()
        if any(accession in overlap for accession in CURRENT) and independent == "true":
            raise ValueError(
                f"current-accession paper incorrectly labeled independent on line {index}"
            )
    args.outdir.mkdir(parents=True, exist_ok=True)
    audit = args.outdir / "published_evidence_audit.tsv"
    summary = args.outdir / "published_evidence_summary.md"
    manifest = args.outdir / "published_evidence.sha256"
    with audit.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value", "status"])
        writer.writerow(["registry_rows", len(records), "PASS"])
        writer.writerow([
            "independent_rows",
            sum(row["independent_of_current_datasets"].lower() == "true" for row in records),
            "INFO",
        ])
        writer.writerow([
            "same_current_accession_rows",
            sum(any(accession in row["accession_overlap"].upper() for accession in CURRENT)
                for row in records),
            "INFO",
        ])
        writer.writerow([
            "unresolved_independence_rows",
            sum(row["independent_of_current_datasets"].lower() == "unresolved" for row in records),
            "WARN",
        ])
    summary.write_text("\n".join([
        "# Published evidence registry", "",
        f"- Registered sources: {len(records)}.",
        f"- Independent of all current datasets: {sum(row['independent_of_current_datasets'].lower() == 'true' for row in records)}.",
        "- Sources reusing a current accession are prior interpretation, not validation.",
        "- Candidate support requires an exact gene/pathway link; contextual papers are not promoted automatically.", "",
    ]), encoding="utf-8")
    with manifest.open("w") as handle:
        for path in (args.registry, args.config, audit, summary):
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"published evidence registry: {len(records)} rows PASS")


if __name__ == "__main__":
    main()
