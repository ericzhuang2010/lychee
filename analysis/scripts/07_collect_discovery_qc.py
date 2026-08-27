#!/usr/bin/env python3
"""Collect preregistered technical gates from fastp, STAR, BAM, and Salmon."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def star_log(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open() as handle:
        for line in handle:
            if "|" in line:
                key, value = line.split("|", 1)
                values[key.strip()] = value.strip()
    return values


def percent(raw: str) -> float:
    return float(raw.rstrip("%"))


def idxstats(path: Path) -> tuple[int, int, int]:
    host = pathogen = unmapped = 0
    with path.open() as handle:
        for line in handle:
            contig, _, mapped, unmap = line.rstrip("\n").split("\t")
            mapped_count, unmapped_count = int(mapped), int(unmap)
            if contig.startswith("HOST_"):
                host += mapped_count
            elif contig.startswith("PATH_"):
                pathogen += mapped_count
            elif contig == "*":
                unmapped += unmapped_count
    return host, pathogen, unmapped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True)
    parser.add_argument("--qc-root", required=True)
    parser.add_argument("--alignment-root", required=True)
    parser.add_argument("--salmon-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--decisions", required=True)
    args = parser.parse_args()

    with Path(args.samples).open() as handle:
        samples = list(csv.DictReader(handle, delimiter="\t"))
    rows: list[dict[str, object]] = []
    decisions: list[dict[str, str]] = []
    for sample in samples:
        sample_id = sample["sample_id"]
        with (Path(args.qc_root) / "fastp" / f"{sample_id}.json").open() as handle:
            fastp = json.load(handle)
        star = star_log(Path(args.alignment_root) / sample_id / "Log.final.out")
        host, pathogen, unmapped = idxstats(
            Path(args.alignment_root) / sample_id / "idxstats.tsv"
        )
        with (Path(args.salmon_root) / sample_id / "aux_info" / "meta_info.json").open() as handle:
            salmon = json.load(handle)

        before_reads = int(fastp["summary"]["before_filtering"]["total_reads"])
        after_reads = int(fastp["summary"]["after_filtering"]["total_reads"])
        surviving_pairs = after_reads // 2
        unique_percent = percent(star["Uniquely mapped reads %"])
        assigned = host + pathogen
        host_fraction = host / assigned if assigned else 0.0
        pathogen_fraction = pathogen / assigned if assigned else 0.0
        failure_reasons: list[str] = []
        if surviving_pairs < 10_000_000:
            failure_reasons.append("fewer_than_10_million_surviving_read_pairs")
        if unique_percent < 40:
            failure_reasons.append("less_than_40_percent_uniquely_mapped")
        status = "EXCLUDE_PRIMARY" if failure_reasons else "INCLUDE"
        reason = ";".join(failure_reasons) if failure_reasons else "none"

        rows.append(
            {
                "sample_id": sample_id,
                "run": sample["run"],
                "cultivar": sample["cultivar"],
                "treatment": sample["treatment"],
                "input_read_pairs": before_reads // 2,
                "surviving_read_pairs": surviving_pairs,
                "fastp_survival_fraction": after_reads / before_reads,
                "q30_rate_after": fastp["summary"]["after_filtering"]["q30_rate"],
                "star_input_reads": int(star["Number of input reads"]),
                "star_unique_percent": unique_percent,
                "star_multi_percent": percent(star["% of reads mapped to multiple loci"]),
                "star_mismatch_percent": percent(star["Mismatch rate per base, %"]),
                "host_mapped_alignments": host,
                "pathogen_mapped_alignments": pathogen,
                "unmapped_alignments": unmapped,
                "host_fraction_of_host_pathogen": host_fraction,
                "pathogen_fraction_of_host_pathogen": pathogen_fraction,
                "salmon_mapping_rate": float(salmon["percent_mapped"]) / 100,
                "technical_gate": status,
                "technical_gate_reason": reason,
            }
        )
        decisions.append(
            {
                "sample_id": sample_id,
                "primary_status": status,
                "reason": reason,
                "all_sample_sensitivity": "retain",
            }
        )

    report = Path(args.report)
    decisions_path = Path(args.decisions)
    report.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0])
    with report.open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with decisions_path.open("w") as handle:
        columns = ["sample_id", "primary_status", "reason", "all_sample_sensitivity"]
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(decisions)


if __name__ == "__main__":
    main()
