#!/usr/bin/env python3
"""Audit the acquired PmiREN bulk catalogue for a prespecified litchi reference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    provenance = json.loads(args.provenance.read_text())
    observed_sha = sha256(args.archive)
    if observed_sha != provenance["archive_sha256"]:
        raise ValueError("PmiREN archive checksum differs from frozen provenance")
    with zipfile.ZipFile(args.archive) as archive:
        names = archive.namelist()
        bad = archive.testzip()
    if bad is not None:
        raise ValueError(f"PmiREN archive CRC failure: {bad}")
    species = sorted({
        name.split("/")[1]
        for name in names
        if name.startswith("ftp-download/") and len(name.split("/")) >= 3
    })
    exact_species = [name for name in species if name.startswith("Litchi_chinensis_")]
    mature_files = [
        name for name in names
        if "Litchi_chinensis" in name and name.endswith("_mature.fa")
    ]
    status = "PASS" if exact_species and mature_files else "NOT_TESTABLE_REFERENCE_ABSENT"
    reason = (
        "exact_Litchi_chinensis_mature_reference_present"
        if status == "PASS"
        else "no_Litchi_chinensis_species_directory_or_mature_fasta_in_acquired_official_bulk_archive"
    )

    args.outdir.mkdir(parents=True, exist_ok=True)
    gate_path = args.outdir / "small_rna_reference_gate.tsv"
    catalogue_path = args.outdir / "pmiren_species_catalogue.tsv"
    summary_path = args.outdir / "small_rna_reference_summary.md"
    manifest_path = args.outdir / "small_rna_reference.sha256"
    with catalogue_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["catalogue_entry", "is_exact_litchi_chinensis"])
        for name in species:
            writer.writerow([name, str(name in exact_species).lower()])
    with gate_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "resource", "upstream_modified_utc", "archive_sha256", "archive_file_count",
            "species_catalogue_entries", "exact_litchi_species_entries", "litchi_mature_files",
            "reference_gate_status", "reason", "allowed_next_action",
        ])
        writer.writerow([
            provenance["resource"], provenance["upstream_modified_utc"], observed_sha,
            len(names), len(species), len(exact_species), len(mature_files), status, reason,
            (
                "quantify_prespecified_known_mature_miRNAs"
                if status == "PASS"
                else "emit_NOT_TESTABLE; study-derived_novel_miRNAs_remain_exploratory_only"
            ),
        ])
    summary_path.write_text("\n".join([
        "# PmiREN litchi reference availability", "",
        f"- Acquired official bulk archive entries: {len(names)} files across {len(species)} species directories.",
        f"- Exact `Litchi chinensis` species entries: {len(exact_species)}.",
        f"- Exact litchi mature-miRNA FASTA files: {len(mature_files)}.",
        f"- Frozen known-miRNA reference gate: **{status}**.",
        "- No study-derived sequence is promoted to the frozen known-miRNA reference.",
        "- This status concerns reference availability, not a biological outcome.", "",
    ]), encoding="utf-8")
    with manifest_path.open("w") as handle:
        for path in (
            args.archive, args.provenance, args.config, gate_path, catalogue_path, summary_path
        ):
            handle.write(f"{sha256(path)}  {path}\n")
    print(
        f"PmiREN audit: {len(species)} species; litchi entries={len(exact_species)}; {status}"
    )


if __name__ == "__main__":
    main()
