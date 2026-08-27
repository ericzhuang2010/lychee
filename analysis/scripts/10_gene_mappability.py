#!/usr/bin/env python3
"""Summarize uniform GenMap scores and exon-model ambiguity for every host gene."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ATTRIBUTE = re.compile(r'(?:^|;)\s*([A-Za-z0-9_.:-]+)\s+["\']?([^;"\']+)["\']?')


@dataclass(frozen=True)
class Exon:
    sequence: str
    start: int
    end: int
    gene: str


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def parse_attributes(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in ATTRIBUTE.finditer(text)}


def merge_intervals(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(values):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return [(start, end) for start, end in merged]


def read_union_exons(path: Path) -> tuple[list[Exon], dict[str, int]]:
    raw: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    with open_text(path) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            attributes = parse_attributes(fields[8])
            gene = attributes.get("gene_id") or attributes.get("gene") or attributes.get("Parent")
            if not gene:
                raise ValueError(f"Exon lacks a gene identifier: {line.rstrip()}")
            # GTF is 1-based closed; BED/bedGraph is 0-based half-open.
            raw[(fields[0], gene)].append((int(fields[3]) - 1, int(fields[4])))
    if not raw:
        raise ValueError(f"No exons found in {path}")
    exons: list[Exon] = []
    lengths: dict[str, int] = defaultdict(int)
    for (sequence, gene), intervals in raw.items():
        for start, end in merge_intervals(intervals):
            if end <= start:
                raise ValueError(f"Invalid exon coordinates for {gene}")
            exons.append(Exon(sequence, start, end, gene))
            lengths[gene] += end - start
    exons.sort(key=lambda item: (item.sequence, item.start, item.end, item.gene))
    return exons, dict(lengths)


def find_overlapping_gene_models(exons: list[Exon]) -> dict[str, set[str]]:
    overlaps: dict[str, set[str]] = defaultdict(set)
    active: list[Exon] = []
    previous_sequence = None
    for exon in exons:
        if exon.sequence != previous_sequence:
            active = []
            previous_sequence = exon.sequence
        active = [other for other in active if other.end > exon.start]
        for other in active:
            if other.gene != exon.gene and other.start < exon.end:
                overlaps[exon.gene].add(other.gene)
                overlaps[other.gene].add(exon.gene)
        active.append(exon)
    return overlaps


def summarize_bedgraph(
    path: Path,
    exons: list[Exon],
    unique_score: float,
    tolerance: float,
) -> tuple[dict[str, int], dict[str, int], set[str]]:
    by_sequence: dict[str, list[Exon]] = defaultdict(list)
    for exon in exons:
        by_sequence[exon.sequence].append(exon)
    scored: dict[str, int] = defaultdict(int)
    unique: dict[str, int] = defaultdict(int)
    observed_sequences: set[str] = set()
    positions: dict[str, int] = defaultdict(int)
    active: dict[str, list[Exon]] = defaultdict(list)
    last_start: dict[str, int] = {}

    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.rstrip("\n").split()
            if len(fields) < 4:
                raise ValueError(f"Malformed bedGraph line {line_number}: {line.rstrip()}")
            sequence, start_text, end_text, score_text = fields[:4]
            if sequence not in by_sequence:
                continue
            start, end = int(start_text), int(end_text)
            score = float(score_text)
            if not math.isfinite(score) or end <= start:
                continue
            if sequence in last_start and start < last_start[sequence]:
                raise ValueError(f"bedGraph is not coordinate sorted on {sequence}")
            last_start[sequence] = start
            observed_sequences.add(sequence)
            sequence_exons = by_sequence[sequence]
            index = positions[sequence]
            current = [value for value in active[sequence] if value.end > start]
            while index < len(sequence_exons) and sequence_exons[index].start < end:
                candidate = sequence_exons[index]
                if candidate.end > start:
                    current.append(candidate)
                index += 1
            positions[sequence] = index
            active[sequence] = current
            is_unique = abs(score - unique_score) <= tolerance
            for exon in current:
                overlap = min(end, exon.end) - max(start, exon.start)
                if overlap > 0:
                    scored[exon.gene] += overlap
                    if is_unique:
                        unique[exon.gene] += overlap
    return dict(scored), dict(unique), observed_sequences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtf", required=True)
    parser.add_argument("--bedgraph", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--selection")
    parser.add_argument("--index-dir")
    parser.add_argument("--checksum-manifest")
    args = parser.parse_args()

    with Path(args.config).open() as handle:
        settings = json.load(handle)["mappability"]
    exons, exon_lengths = read_union_exons(Path(args.gtf))
    overlaps = find_overlapping_gene_models(exons)
    scored, unique, observed_sequences = summarize_bedgraph(
        Path(args.bedgraph),
        exons,
        float(settings["unique_score"]),
        float(settings["unique_score_tolerance"]),
    )
    annotated_sequences = {exon.sequence for exon in exons}
    if not observed_sequences:
        raise ValueError("No annotated host sequence had a mappability score")
    missing_sequences = annotated_sequences - observed_sequences

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "gene_id", "union_exon_bases", "scored_exonic_bases",
        "unique_exonic_bases", "fraction_exonic_bases_scored",
        "fraction_unique_mappability", "mappability_status",
        "overlapping_gene_count", "overlapping_genes",
        "unique_gene_model_status", "uniform_gene_qc_status",
    ]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for gene in sorted(exon_lengths):
            total = exon_lengths[gene]
            scored_bases = scored.get(gene, 0)
            unique_bases = unique.get(gene, 0)
            fraction_scored = scored_bases / total
            fraction_unique = unique_bases / scored_bases if scored_bases else 0.0
            mappability_pass = (
                scored_bases >= int(settings["minimum_scored_exonic_bases"])
                and fraction_unique >= float(settings["minimum_unique_exonic_fraction"])
            )
            overlapping = sorted(overlaps.get(gene, set()))
            model_pass = not overlapping
            writer.writerow({
                "gene_id": gene,
                "union_exon_bases": total,
                "scored_exonic_bases": scored_bases,
                "unique_exonic_bases": unique_bases,
                "fraction_exonic_bases_scored": f"{fraction_scored:.8f}",
                "fraction_unique_mappability": f"{fraction_unique:.8f}",
                "mappability_status": "PASS" if mappability_pass else "FAIL",
                "overlapping_gene_count": len(overlapping),
                "overlapping_genes": ";".join(overlapping),
                "unique_gene_model_status": "PASS" if model_pass else "FAIL",
                "uniform_gene_qc_status": "PASS" if mappability_pass and model_pass else "FAIL",
            })
    if missing_sequences:
        print(
            "WARNING: annotated sequences without mappability rows: "
            + ",".join(sorted(missing_sequences))
        )
    print(
        f"gene mappability PASS: {sum(1 for gene in exon_lengths if scored.get(gene, 0) >= int(settings['minimum_scored_exonic_bases']) and unique.get(gene, 0) / max(scored.get(gene, 0), 1) >= float(settings['minimum_unique_exonic_fraction']))}/{len(exon_lengths)}"
    )
    if args.checksum_manifest:
        frozen_paths = [
            Path(args.gtf), Path(args.bedgraph), Path(args.config), output,
        ]
        if args.selection:
            frozen_paths.append(Path(args.selection))
        if args.index_dir:
            frozen_paths.extend(
                sorted(path for path in Path(args.index_dir).rglob("*") if path.is_file())
            )
        project = Path.cwd().resolve()
        lines = []
        for frozen_path in frozen_paths:
            digest = hashlib.sha256()
            with frozen_path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            resolved = frozen_path.resolve()
            try:
                label = resolved.relative_to(project)
            except ValueError:
                label = resolved
            lines.append(f"{digest.hexdigest()}  {label}")
        manifest = Path(args.checksum_manifest)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("\n".join(lines) + "\n")
        print(f"wrote {len(lines)} frozen mappability checksums to {manifest}")


if __name__ == "__main__":
    main()
