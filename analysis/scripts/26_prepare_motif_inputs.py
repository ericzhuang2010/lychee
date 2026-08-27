#!/usr/bin/env python3
"""Extract canonical promoters and build deterministic expression/GC-matched backgrounds."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

import pysam


ATTRIBUTE = re.compile(r'(\S+) "([^"]+)"')


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1]


def quantile_breaks(values: list[float], bins: int) -> list[float]:
    ordered = sorted(values)
    return [ordered[min(len(ordered) - 1, math.ceil(len(ordered) * i / bins) - 1)]
            for i in range(1, bins)]


def assign_bin(value: float, breaks: list[float]) -> int:
    return bisect.bisect_left(breaks, value) + 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_fasta(path: Path, rows: list[dict[str, object]], sequences: dict[tuple[str, int], str], window: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            gene = str(row["gene_id"])
            sequence = sequences[(gene, window)]
            handle.write(f">{gene} window={window}\n")
            for start in range(0, len(sequence), 80):
                handle.write(sequence[start:start + 80] + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-genes", required=True, type=Path)
    parser.add_argument("--normalized-counts", required=True, type=Path)
    parser.add_argument("--gene-qc", required=True, type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--gtf", required=True, type=Path)
    parser.add_argument("--genome", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text())["motifs"]
    windows = sorted(map(int, config["promoter_windows_bp"]))
    sets = int(config["matched_background_sets"])
    minimum_genes = int(config["minimum_frozen_genes"])
    seed = int(config["seed"])
    bins = 5

    frozen_rows = read_tsv(args.frozen_genes)
    frozen = {row["gene_id"] for row in frozen_rows}
    normalized_rows = read_tsv(args.normalized_counts)
    means: dict[str, float] = {}
    for row in normalized_rows:
        values = [float(value) for key, value in row.items() if key != "gene_id" and value not in ("", "NA")]
        means[row["gene_id"]] = sum(values) / len(values) if values else math.nan
    qc = {row["gene_id"]: row for row in read_tsv(args.gene_qc)}
    canonical = {row["canonical_transcript_id"]: row["gene_id"] for row in read_tsv(args.canonical)}

    transcript_bounds: dict[str, list[object]] = {}
    with args.gtf.open() as handle:
        for raw in handle:
            if raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            attributes = dict(ATTRIBUTE.findall(fields[8]))
            transcript = attributes.get("transcript_id")
            if transcript not in canonical:
                continue
            start, end = int(fields[3]), int(fields[4])
            if transcript not in transcript_bounds:
                transcript_bounds[transcript] = [fields[0], start, end, fields[6]]
            else:
                bounds = transcript_bounds[transcript]
                if fields[0] != bounds[0] or fields[6] != bounds[3]:
                    raise ValueError(f"canonical transcript spans contigs/strands: {transcript}")
                bounds[1] = min(int(bounds[1]), start)
                bounds[2] = max(int(bounds[2]), end)

    gene_bounds: dict[str, tuple[str, int, str]] = {}
    for transcript, gene in canonical.items():
        if transcript not in transcript_bounds:
            raise ValueError(f"canonical transcript absent from GTF: {transcript}")
        contig, start, end, strand = transcript_bounds[transcript]
        tss = int(start) if strand == "+" else int(end)
        gene_bounds[gene] = (str(contig), tss, str(strand))

    genome = pysam.FastaFile(str(args.genome))
    lengths = dict(zip(genome.references, genome.lengths, strict=True))
    sequences: dict[tuple[str, int], str] = {}
    metadata: list[dict[str, object]] = []
    for gene in sorted(gene_bounds):
        contig, tss, strand = gene_bounds[gene]
        if contig not in lengths:
            raise ValueError(f"GTF contig missing from FASTA: {contig}")
        for window in windows:
            if strand == "+":
                start0, end0 = max(0, tss - 1 - window), tss - 1
                sequence = genome.fetch(contig, start0, end0).upper()
            else:
                start0, end0 = tss, min(lengths[contig], tss + window)
                sequence = reverse_complement(genome.fetch(contig, start0, end0).upper())
            non_n = sum(base in "ACGT" for base in sequence)
            gc = sum(base in "GC" for base in sequence)
            fraction_non_n = non_n / len(sequence) if sequence else 0.0
            gc_fraction = gc / non_n if non_n else math.nan
            sequences[(gene, window)] = sequence
            metadata.append({
                "gene_id": gene, "contig": contig, "strand": strand, "tss_1based": tss,
                "window_bp": window, "start_0based": start0, "end_0based": end0,
                "sequence_length": len(sequence), "fraction_non_n": fraction_non_n,
                "gc_fraction": gc_fraction, "mean_normalized_count": means.get(gene, math.nan),
                "uniform_gene_qc_status": qc.get(gene, {}).get("uniform_gene_qc_status", "MISSING"),
                "frozen_gene": gene in frozen,
            })
    genome.close()

    args.outdir.mkdir(parents=True, exist_ok=True)
    metadata_path = args.outdir / "promoter_metadata.tsv"
    gate_path = args.outdir / "motif_gate.tsv"
    assignment_path = args.outdir / "background_assignments.tsv"
    manifest_path = args.outdir / "motif_inputs.sha256"
    metadata_fields = [
        "gene_id", "contig", "strand", "tss_1based", "window_bp", "start_0based",
        "end_0based", "sequence_length", "fraction_non_n", "gc_fraction",
        "mean_normalized_count", "uniform_gene_qc_status", "frozen_gene",
    ]
    write_tsv(metadata_path, metadata_fields, metadata)

    by_window = defaultdict(dict)
    for row in metadata:
        by_window[int(row["window_bp"])][str(row["gene_id"])] = row
    assignment_rows: list[dict[str, object]] = []
    generated_files: list[Path] = [metadata_path, gate_path, assignment_path]
    gate_rows: list[dict[str, object]] = []
    for window in windows:
        window_rows = by_window[window]
        eligible = [
            row for row in window_rows.values()
            if row["uniform_gene_qc_status"] == "PASS"
            and float(row["fraction_non_n"]) >= 0.80
            and math.isfinite(float(row["gc_fraction"]))
            and math.isfinite(float(row["mean_normalized_count"]))
        ]
        candidates = [window_rows[gene] for gene in sorted(frozen) if gene in window_rows]
        valid_candidates = [row for row in candidates if row in eligible]
        candidate_path = args.outdir / f"frozen_candidates_{window}bp.fa"
        write_fasta(candidate_path, valid_candidates, sequences, window)
        generated_files.append(candidate_path)
        status = "PASS" if len(valid_candidates) >= minimum_genes else "NOT_TESTABLE"
        reason = (
            "minimum_frozen_genes_met" if status == "PASS"
            else "fewer_than_minimum_frozen_genes_with_valid_promoters"
        )
        gate_rows.append({
            "window_bp": window, "frozen_genes": len(frozen),
            "valid_candidate_promoters": len(valid_candidates), "minimum_required": minimum_genes,
            "motif_gate_status": status, "reason": reason,
        })
        if status != "PASS":
            continue

        expression_breaks = quantile_breaks(
            [math.log1p(float(row["mean_normalized_count"])) for row in eligible], bins
        )
        gc_breaks = quantile_breaks([float(row["gc_fraction"]) for row in eligible], bins)
        for row in eligible:
            row["expression_bin"] = assign_bin(
                math.log1p(float(row["mean_normalized_count"])), expression_breaks
            )
            row["gc_bin"] = assign_bin(float(row["gc_fraction"]), gc_breaks)
        pool = [row for row in eligible if row["gene_id"] not in frozen]
        if len(pool) < len(valid_candidates):
            raise ValueError("insufficient valid noncandidate promoter pool")
        for replicate in range(1, sets + 1):
            rng = random.Random(seed + window * 1000 + replicate)
            tie_order = {str(row["gene_id"]): rng.random() for row in pool}
            unused = {str(row["gene_id"]): row for row in pool}
            chosen: list[dict[str, object]] = []
            for candidate in valid_candidates:
                target_expression = int(candidate["expression_bin"])
                target_gc = int(candidate["gc_bin"])
                ranked = sorted(
                    unused.values(),
                    key=lambda row: (
                        abs(int(row["expression_bin"]) - target_expression)
                        + abs(int(row["gc_bin"]) - target_gc),
                        tie_order[str(row["gene_id"])], str(row["gene_id"]),
                    ),
                )
                selected = ranked[0]
                chosen.append(selected)
                unused.pop(str(selected["gene_id"]))
                assignment_rows.append({
                    "window_bp": window, "replicate": replicate,
                    "candidate_gene_id": candidate["gene_id"],
                    "background_gene_id": selected["gene_id"],
                    "candidate_expression_bin": target_expression,
                    "background_expression_bin": selected["expression_bin"],
                    "candidate_gc_bin": target_gc, "background_gc_bin": selected["gc_bin"],
                    "manhattan_bin_distance": (
                        abs(int(selected["expression_bin"]) - target_expression)
                        + abs(int(selected["gc_bin"]) - target_gc)
                    ),
                })
            background_path = args.outdir / "backgrounds" / str(window) / f"replicate_{replicate:03d}.fa"
            write_fasta(background_path, chosen, sequences, window)
            generated_files.append(background_path)

    write_tsv(
        gate_path,
        ["window_bp", "frozen_genes", "valid_candidate_promoters", "minimum_required", "motif_gate_status", "reason"],
        gate_rows,
    )
    write_tsv(
        assignment_path,
        [
            "window_bp", "replicate", "candidate_gene_id", "background_gene_id",
            "candidate_expression_bin", "background_expression_bin", "candidate_gc_bin",
            "background_gc_bin", "manhattan_bin_distance",
        ],
        assignment_rows,
    )
    with manifest_path.open("w") as handle:
        for path in (
            args.frozen_genes, args.normalized_counts, args.gene_qc, args.canonical,
            args.gtf, args.genome, args.config, *generated_files,
        ):
            handle.write(f"{sha256(path)}  {path}\n")
    print(
        f"motif inputs: {len(frozen)} frozen genes; "
        + ", ".join(f"{row['window_bp']}bp={row['motif_gate_status']}" for row in gate_rows)
    )


if __name__ == "__main__":
    main()
