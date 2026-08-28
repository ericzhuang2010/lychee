#!/usr/bin/env python3
"""Controlled background comparison for the 18 exploratory promoters.

The foreground statistic and seven exact motif classes are held fixed while the
background is changed from simulated 34%-GC sequence to genomic promoters
matched on expression and GC quintiles. The original observed-motif input TSV
was not included in the archived exploratory supplement, so published observed
totals are retained as the fixed test statistics and exact-sequence recounts
from the current canonical promoters are reported as a provenance diagnostic.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pysam


MOTIFS = [
    ("ABRE", "ACGTG", 45, 38.44, 0.16402, 0.22963, "explicitly stated in exploratory manuscript"),
    ("ARE", "AAACCA", 46, 24.61, 0.00011, 0.00026, "explicitly stated in exploratory manuscript"),
    ("AT-rich sequence", "TAAAATACT", 3, 1.71, 0.24643, 0.28750, "explicitly stated in exploratory manuscript"),
    ("MBS", "CAACTG", 9, 12.68, 0.88396, 0.88396, "explicitly stated in exploratory manuscript"),
    ("MeJA-responsive", "CGTCA", 54, 38.44, 0.01026, 0.01795, "CGTCA plus reverse-complement TGACG stated in manuscript"),
    ("TCA-element", "CCATCTTTTT", 9, 0.19, 0.00001, 0.00003, "standard PlantCARE variant; exact original input TSV was not archived"),
    ("TC-rich repeats", "GTTTTCTTAC", 10, 0.15, 0.00001, 0.00003, "explicitly stated in exploratory manuscript"),
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1].upper()


def count_motif(sequence: str | bytes, motif: str) -> int:
    if isinstance(sequence, bytes):
        target = motif.encode("ascii")
        rc = reverse_complement(motif).encode("ascii")
    else:
        sequence = sequence.upper()
        target = motif
        rc = reverse_complement(motif)
    count = sequence.count(target)
    if rc != target:
        count += sequence.count(rc)
    return count


def quantile_breaks(values: list[float], bins: int = 5) -> list[float]:
    ordered = sorted(values)
    return [ordered[min(len(ordered) - 1, math.ceil(len(ordered) * i / bins) - 1)] for i in range(1, bins)]


def assign_bin(value: float, breaks: list[float]) -> int:
    return bisect.bisect_left(breaks, value) + 1


def bh_adjust(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda key: (values[key], key))
    adjusted: dict[str, float] = {}
    running = 1.0
    m = len(ordered)
    for rank in range(m, 0, -1):
        key = ordered[rank - 1]
        running = min(running, values[key] * m / rank)
        adjusted[key] = min(1.0, running)
    return adjusted


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sequence_for(row: dict[str, str], genome: pysam.FastaFile) -> str:
    sequence = genome.fetch(row["contig"], int(row["start_0based"]), int(row["end_0based"])).upper()
    return reverse_complement(sequence) if row["strand"] == "-" else sequence


def genomic_backgrounds(
    metadata: list[dict[str, str]], legacy: list[str], genome_path: Path, sets: int, seed: int
) -> tuple[dict[str, list[int]], dict[str, str], list[dict[str, object]]]:
    rows = {row["gene_id"]: row for row in metadata if int(row["window_bp"]) == 2000}
    missing = sorted(set(legacy) - set(rows))
    if missing:
        raise ValueError(f"legacy genes missing promoter metadata: {missing}")
    eligible = [
        row for row in rows.values()
        if row["uniform_gene_qc_status"] == "PASS"
        and float(row["fraction_non_n"]) >= 0.80
        and math.isfinite(float(row["gc_fraction"]))
        and math.isfinite(float(row["mean_normalized_count"]))
    ]
    expression_breaks = quantile_breaks([math.log1p(float(row["mean_normalized_count"])) for row in eligible])
    gc_breaks = quantile_breaks([float(row["gc_fraction"]) for row in eligible])
    for row in rows.values():
        if math.isfinite(float(row["mean_normalized_count"])) and math.isfinite(float(row["gc_fraction"])):
            row["expression_bin"] = str(assign_bin(math.log1p(float(row["mean_normalized_count"])), expression_breaks))
            row["gc_bin"] = str(assign_bin(float(row["gc_fraction"]), gc_breaks))
    candidates = [rows[gene] for gene in legacy]
    pool = [row for row in eligible if row["gene_id"] not in set(legacy)]
    assignments: list[dict[str, object]] = []
    selected_by_set: list[list[dict[str, str]]] = []
    for replicate in range(1, sets + 1):
        rng = random.Random(seed + 2000 * 1000 + replicate)
        tie_order = {row["gene_id"]: rng.random() for row in pool}
        unused = {row["gene_id"]: row for row in pool}
        chosen: list[dict[str, str]] = []
        for candidate in candidates:
            target_expression = int(candidate["expression_bin"])
            target_gc = int(candidate["gc_bin"])
            selected = min(
                unused.values(),
                key=lambda row: (
                    abs(int(row["expression_bin"]) - target_expression) + abs(int(row["gc_bin"]) - target_gc),
                    tie_order[row["gene_id"]], row["gene_id"],
                ),
            )
            chosen.append(selected)
            unused.pop(selected["gene_id"])
            assignments.append({
                "replicate": replicate,
                "candidate_gene_id": candidate["gene_id"],
                "background_gene_id": selected["gene_id"],
                "candidate_expression_bin": target_expression,
                "background_expression_bin": selected["expression_bin"],
                "candidate_gc_bin": target_gc,
                "background_gc_bin": selected["gc_bin"],
                "manhattan_bin_distance": abs(int(selected["expression_bin"]) - target_expression) + abs(int(selected["gc_bin"]) - target_gc),
            })
        selected_by_set.append(chosen)

    genome = pysam.FastaFile(str(genome_path))
    candidate_sequences = {row["gene_id"]: sequence_for(row, genome) for row in candidates}
    sequence_cache: dict[str, str] = {}
    counts = {element: [] for element, *_ in MOTIFS}
    for chosen in selected_by_set:
        sequences = []
        for row in chosen:
            gene = row["gene_id"]
            if gene not in sequence_cache:
                sequence_cache[gene] = sequence_for(row, genome)
            sequences.append(sequence_cache[gene])
        for element, motif, *_ in MOTIFS:
            counts[element].append(sum(count_motif(sequence, motif) for sequence in sequences))
    genome.close()
    return counts, candidate_sequences, assignments


def simulated_backgrounds(sets: int, seed: int, chunk_size: int) -> dict[str, np.ndarray]:
    """Generate 34%-GC sets efficiently while preserving promoter boundaries."""
    rng = np.random.default_rng(seed)
    promoter_length = 2000
    n_promoters = 18
    width = n_promoters * (promoter_length + 1)
    separators = np.arange(promoter_length, width, promoter_length + 1)
    lookup = np.empty(100, dtype=np.uint8)
    lookup[:33] = ord("A")
    lookup[33:66] = ord("T")
    lookup[66:83] = ord("G")
    lookup[83:] = ord("C")
    result = {element: np.zeros(sets, dtype=np.int32) for element, *_ in MOTIFS}
    offset = 0
    while offset < sets:
        batch = min(chunk_size, sets - offset)
        draws = rng.integers(0, 100, size=(batch, width), dtype=np.uint8)
        sequences = lookup[draws]
        sequences[:, separators] = ord("N")
        for local in range(batch):
            sequence = sequences[local].tobytes()
            for element, motif, *_ in MOTIFS:
                result[element][offset + local] = count_motif(sequence, motif)
        offset += batch
        print(f"randomized-GC progress: {offset}/{sets}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", required=True, type=Path)
    parser.add_argument("--promoter-metadata", required=True, type=Path)
    parser.add_argument("--genome", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--supplement", required=True, type=Path)
    parser.add_argument("--random-sets", type=int, default=100000)
    parser.add_argument("--chunk-size", type=int, default=500)
    args = parser.parse_args()

    legacy = [row["gene_id"] for row in read_tsv(args.legacy)]
    if len(legacy) != 18 or len(set(legacy)) != 18:
        raise ValueError("legacy foreground must contain 18 unique genes")
    metadata = read_tsv(args.promoter_metadata)
    config = json.loads(args.config.read_text(encoding="utf-8"))["motifs"]
    genomic_sets = int(config["matched_background_sets"])
    genomic_counts, candidate_sequences, assignments = genomic_backgrounds(
        metadata, legacy, args.genome, genomic_sets, int(config["seed"])
    )
    simulated_counts = simulated_backgrounds(args.random_sets, 2024, args.chunk_size)

    candidate_recounts = {
        element: sum(count_motif(sequence, motif) for sequence in candidate_sequences.values())
        for element, motif, *_ in MOTIFS
    }
    rows: list[dict[str, object]] = []
    p_by_strategy: dict[str, dict[str, float]] = {"randomized_GC_rerun": {}, "expression_GC_matched_genomic": {}}
    pending: list[tuple[str, str, int, float, float, str, int, float, float, float]] = []
    for element, motif, observed, reported_mean, reported_p, reported_q, provenance in MOTIFS:
        random_values = simulated_counts[element]
        random_p = (1 + int(np.sum(random_values >= observed))) / (1 + len(random_values))
        genomic_values = np.asarray(genomic_counts[element], dtype=float)
        genomic_p = (1 + int(np.sum(genomic_values >= observed))) / (1 + len(genomic_values))
        p_by_strategy["randomized_GC_rerun"][element] = random_p
        p_by_strategy["expression_GC_matched_genomic"][element] = genomic_p
        pending.extend([
            (element, "reported_randomized_GC", 100000, reported_mean, math.nan, motif, observed, reported_p, reported_q, provenance),
            (element, "randomized_GC_rerun", len(random_values), float(np.mean(random_values)), float(np.std(random_values, ddof=1)), motif, observed, random_p, math.nan, provenance),
            (element, "expression_GC_matched_genomic", len(genomic_values), float(np.mean(genomic_values)), float(np.std(genomic_values, ddof=1)), motif, observed, genomic_p, math.nan, provenance),
        ])
    adjusted = {strategy: bh_adjust(values) for strategy, values in p_by_strategy.items()}
    for element, strategy, n_sets, mean, sd, motif, observed, p_value, q_value, provenance in pending:
        if strategy in adjusted:
            q_value = adjusted[strategy][element]
        rows.append({
            "element": element,
            "motif": motif,
            "motif_provenance": provenance,
            "published_observed_total_fixed": observed,
            "canonical_promoter_recount": candidate_recounts[element],
            "recount_matches_published": candidate_recounts[element] == observed,
            "background_strategy": strategy,
            "background_sets": n_sets,
            "background_mean": mean,
            "background_sd": sd,
            "empirical_p": p_value,
            "bh_q": q_value,
            "enriched_q_lt_0_05": q_value < 0.05,
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        args.supplement,
        rows,
        ["element", "motif", "motif_provenance", "published_observed_total_fixed", "canonical_promoter_recount", "recount_matches_published", "background_strategy", "background_sets", "background_mean", "background_sd", "empirical_p", "bh_q", "enriched_q_lt_0_05"],
    )
    write_tsv(
        args.outdir / "background_assignments.tsv",
        assignments,
        ["replicate", "candidate_gene_id", "background_gene_id", "candidate_expression_bin", "background_expression_bin", "candidate_gc_bin", "background_gc_bin", "manhattan_bin_distance"],
    )
    diagnostic_rows = []
    for element, motif, observed, *_ in MOTIFS:
        diagnostic_rows.append({"element": element, "motif": motif, "published_total": observed, "canonical_recount": candidate_recounts[element]})
    for alternate in ("GAGAAGAATA", "TCAGAAGAGG", "CAGAAAAGGA"):
        diagnostic_rows.append({
            "element": "TCA-element sensitivity", "motif": alternate, "published_total": 9,
            "canonical_recount": sum(count_motif(sequence, alternate) for sequence in candidate_sequences.values()),
        })
    write_tsv(args.outdir / "foreground_recount_diagnostics.tsv", diagnostic_rows, ["element", "motif", "published_total", "canonical_recount"])
    manifest = args.outdir / "H5_manifest.sha256"
    with manifest.open("w", encoding="utf-8") as handle:
        for path in (args.legacy, args.promoter_metadata, args.genome, args.config, args.supplement, args.outdir / "background_assignments.tsv", args.outdir / "foreground_recount_diagnostics.tsv"):
            handle.write(f"{sha256(path)}  {path}\n")
    genomic_hits = sum(row["enriched_q_lt_0_05"] for row in rows if row["background_strategy"] == "expression_GC_matched_genomic")
    print(f"H5 complete: {genomic_hits}/7 elements enriched against expression/GC-matched genomic backgrounds")


if __name__ == "__main__":
    main()
