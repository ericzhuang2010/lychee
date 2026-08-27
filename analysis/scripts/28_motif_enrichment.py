#!/usr/bin/env python3
"""Run frozen-background AME/FIMO enrichment and one-time STREME/Tomtom discovery."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"))

AME_FIELDS = [
    "rank", "motif_DB", "motif_ID", "motif_alt_ID", "consensus",
    "p-value", "adj_p-value", "E-value", "tests", "FASTA_max",
    "pos", "neg", "PWM_min", "TP", "%TP", "FP", "%FP",
]


def read_ame_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        lines = [line for line in handle if line.strip() and not line.startswith("#")]
    if not lines:
        return []
    first = next(csv.reader([lines[0]], delimiter="\t"))
    if first != AME_FIELDS and len(first) != len(AME_FIELDS):
        raise ValueError(
            f"AME TSV has {len(first)} columns; expected {len(AME_FIELDS)}"
        )
    reader = csv.DictReader(
        lines, delimiter="\t", fieldnames=None if first == AME_FIELDS else AME_FIELDS
    )
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("AME TSV contains a malformed row")
    return rows


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader(); writer.writerows(rows)


def fasta_records(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    name: str | None = None
    chunks: list[str] = []
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    records.append((name, "".join(chunks)))
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
        if name is not None:
            records.append((name, "".join(chunks)))
    return records


def combined_fasta(path: Path, primary: list[tuple[str, str]], control: list[tuple[str, str]]) -> None:
    with path.open("w") as handle:
        for label, records in (("candidate", primary), ("background", control)):
            for name, sequence in records:
                handle.write(f">{label}|{name}\n{sequence}\n")


def fisher_greater(tp: int, fn: int, fp: int, tn: int) -> float:
    positives, negatives = tp + fn, fp + tn
    successes = tp + fp
    total = positives + negatives
    denominator = math.comb(total, successes)
    return min(1.0, sum(
        math.comb(positives, value) * math.comb(negatives, successes - value) / denominator
        for value in range(tp, min(positives, successes) + 1)
        if 0 <= successes - value <= negatives
    ))


def odds_ratio(tp: int, fn: int, fp: int, tn: int) -> float:
    return ((tp + 0.5) * (tn + 0.5)) / ((fn + 0.5) * (fp + 0.5))


def bh_adjust(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda key: (values[key], key))
    result: dict[str, float] = {}
    running = 1.0
    count = len(ordered)
    for rank in range(count, 0, -1):
        key = ordered[rank - 1]
        running = min(running, values[key] * count / rank)
        result[key] = min(1.0, running)
    return result


def median_group_expression(
    normalized: dict[str, dict[str, float]], metadata: list[dict[str, str]], decisions: dict[str, str]
) -> dict[str, float]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in metadata:
        if decisions.get(row["sample_id"]) == "INCLUDE":
            groups[(row["cultivar"], row["treatment"])].append(row["sample_id"])
    result = {}
    for gene, counts in normalized.items():
        medians = [statistics.median(counts[sample] for sample in samples) for samples in groups.values()]
        result[gene] = max(medians) if medians else math.nan
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--motifs", required=True, type=Path)
    parser.add_argument("--tf-map", required=True, type=Path)
    parser.add_argument("--normalized-counts", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--ame", default="ame")
    parser.add_argument("--fimo", default="fimo")
    parser.add_argument("--streme", default="streme")
    parser.add_argument("--tomtom", default="tomtom")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())["motifs"]
    windows = sorted(map(int, config["promoter_windows_bp"]))
    sets = int(config["matched_background_sets"])
    q_max = float(config["replicate_bh_q_max"])
    or_min = float(config["minimum_odds_ratio"])
    passing_min = int(config["minimum_passing_backgrounds"])
    fimo_threshold = float(config["fimo_p_threshold"])
    args.outdir.mkdir(parents=True, exist_ok=True)

    gate = {int(row["window_bp"]): row for row in read_tsv(args.inputs / "motif_gate.tsv")}
    tf_map = {row["matrix_id"]: row for row in read_tsv(args.tf_map)}
    motif_ids = list(tf_map)
    if not motif_ids:
        raise ValueError("TF map has no fixed motifs")
    normalized_rows = read_tsv(args.normalized_counts)
    normalized = {
        row["gene_id"]: {
            sample: float(value) for sample, value in row.items()
            if sample != "gene_id" and value not in ("", "NA")
        }
        for row in normalized_rows
    }
    decisions = {row["sample_id"]: row["primary_status"] for row in read_tsv(args.decisions)}
    group_expression = median_group_expression(normalized, read_tsv(args.metadata), decisions)

    replicate_rows: list[dict[str, object]] = []
    fimo_rows: list[dict[str, object]] = []
    candidate_site_presence: dict[tuple[str, int, str], bool] = {}
    candidate_genes_by_window: dict[int, list[str]] = {}
    generated: list[Path] = []
    for window in windows:
        if gate[window]["motif_gate_status"] != "PASS":
            continue
        primary_path = args.inputs / f"frozen_candidates_{window}bp.fa"
        primary = fasta_records(primary_path)
        candidate_genes_by_window[window] = [name for name, _ in primary]
        pooled: dict[str, str] = {}
        for replicate in range(1, sets + 1):
            control_path = args.inputs / "backgrounds" / str(window) / f"replicate_{replicate:03d}.fa"
            control = fasta_records(control_path)
            pooled.update(control)
            ame_raw = args.outdir / "ame_raw" / str(window) / f"replicate_{replicate:03d}.tsv"
            ame_raw.parent.mkdir(parents=True, exist_ok=True)
            command = [
                args.ame, "--verbose", "1", "--text", "--control", str(control_path),
                "--method", "fisher", "--scoring", "totalhits", "--hit-lo-fraction", "0.25",
                "--evalue-report-threshold", str(config["ame_evalue_report_threshold"]),
                "--noseq", str(primary_path), str(args.motifs),
            ]
            with ame_raw.open("w") as handle:
                subprocess.run(command, stdout=handle, check=True)
            generated.append(ame_raw)
            seen_ame: set[str] = set()
            for row in read_ame_tsv(ame_raw):
                motif = row["motif_ID"]
                seen_ame.add(motif)
                tp, fp = int(row["TP"]), int(row["FP"])
                pos, neg = int(row["pos"]), int(row["neg"])
                ratio = odds_ratio(tp, pos - tp, fp, neg - fp)
                q_value = float(row["adj_p-value"])
                replicate_rows.append({
                    "window_bp": window, "replicate": replicate, "matrix_id": motif,
                    "motif_name": row["motif_alt_ID"], "ame_p": row["p-value"],
                    "ame_q": q_value, "ame_odds_ratio": ratio, "candidate_hits": tp,
                    "candidate_total": pos, "background_hits": fp, "background_total": neg,
                    "ame_replicate_pass": q_value < q_max and ratio >= or_min,
                })
            for motif in set(motif_ids) - seen_ame:
                replicate_rows.append({
                    "window_bp": window, "replicate": replicate, "matrix_id": motif,
                    "motif_name": tf_map[motif]["motif_name"], "ame_p": 1.0, "ame_q": 1.0,
                    "ame_odds_ratio": 0.0, "candidate_hits": 0, "candidate_total": len(primary),
                    "background_hits": 0, "background_total": len(control),
                    "ame_replicate_pass": False,
                })

            with tempfile.TemporaryDirectory(prefix="lychee_fimo_") as tempdir:
                combined = Path(tempdir) / "combined.fa"
                combined_fasta(combined, primary, control)
                completed = subprocess.run([
                    args.fimo, "--text", "--skip-matched-sequence", "--thresh", str(fimo_threshold),
                    str(args.motifs), str(combined),
                ], check=True, capture_output=True, text=True)
            presence: dict[str, set[str]] = defaultdict(set)
            reader = csv.DictReader(
                (line for line in completed.stdout.splitlines() if line and not line.startswith("#")),
                delimiter="\t",
            )
            for row in reader:
                presence[row["motif_id"]].add(row["sequence_name"])
            for motif in motif_ids:
                for gene, _ in primary:
                    key = (motif, window, gene)
                    observed = f"candidate|{gene}" in presence.get(motif, set())
                    if key in candidate_site_presence and candidate_site_presence[key] != observed:
                        raise ValueError("candidate FIMO site presence changed across matched backgrounds")
                    candidate_site_presence[key] = observed
            p_values: dict[str, float] = {}
            counts: dict[str, tuple[int, int, int, int]] = {}
            for motif in motif_ids:
                present = presence.get(motif, set())
                tp = sum(f"candidate|{name}" in present for name, _ in primary)
                fp = sum(f"background|{name}" in present for name, _ in control)
                counts[motif] = (tp, len(primary) - tp, fp, len(control) - fp)
                p_values[motif] = fisher_greater(*counts[motif])
            q_values = bh_adjust(p_values)
            for motif in motif_ids:
                tp, fn, fp, tn = counts[motif]
                ratio = odds_ratio(tp, fn, fp, tn)
                fimo_rows.append({
                    "window_bp": window, "replicate": replicate, "matrix_id": motif,
                    "fimo_p": p_values[motif], "fimo_q": q_values[motif],
                    "fimo_odds_ratio": ratio, "candidate_present": tp,
                    "candidate_total": tp + fn, "background_present": fp,
                    "background_total": fp + tn,
                    "fimo_replicate_pass": q_values[motif] < q_max and ratio >= or_min,
                })

        pooled_path = args.outdir / f"pooled_background_{window}bp.fa"
        with pooled_path.open("w") as handle:
            for name, sequence in sorted(pooled.items()):
                handle.write(f">{name}\n{sequence}\n")
        generated.append(pooled_path)
        streme_dir = args.outdir / f"streme_{window}bp"
        subprocess.run([
            args.streme, "--p", str(primary_path), "--n", str(pooled_path), "--dna",
            "--oc", str(streme_dir), "--nmotifs", str(config["streme_max_motifs"]),
            "--minw", str(config["streme_min_width"]), "--maxw", str(config["streme_max_width"]),
            "--thresh", str(config["streme_p_threshold"]), "--seed", str(config["seed"]),
        ], check=True)
        streme_motifs = streme_dir / "streme.txt"
        tomtom_dir = args.outdir / f"tomtom_{window}bp"
        has_streme_motif = any(line.startswith("MOTIF ") for line in streme_motifs.read_text().splitlines())
        if has_streme_motif:
            subprocess.run([
                args.tomtom, "-oc", str(tomtom_dir), "-thresh", str(config["tomtom_q_threshold"]),
                str(streme_motifs), str(args.motifs),
            ], check=True)
        else:
            tomtom_dir.mkdir(parents=True, exist_ok=True)
            (tomtom_dir / "NO_STREME_MOTIFS.txt").write_text(
                "STREME discovered no motif at the frozen threshold; Tomtom was not applicable.\n"
            )
        generated.extend(path for directory in (streme_dir, tomtom_dir) for path in directory.rglob("*") if path.is_file())

    replicate_fields = [
        "window_bp", "replicate", "matrix_id", "motif_name", "ame_p", "ame_q",
        "ame_odds_ratio", "candidate_hits", "candidate_total", "background_hits",
        "background_total", "ame_replicate_pass",
    ]
    fimo_fields = [
        "window_bp", "replicate", "matrix_id", "fimo_p", "fimo_q", "fimo_odds_ratio",
        "candidate_present", "candidate_total", "background_present", "background_total",
        "fimo_replicate_pass",
    ]
    replicate_path = args.outdir / "ame_matched_background_replicates.tsv"
    fimo_path = args.outdir / "fimo_matched_background_sensitivity.tsv"
    candidate_site_path = args.outdir / "candidate_motif_site_presence.tsv"
    robust_path = args.outdir / "robust_candidate_motifs.tsv"
    summary_path = args.outdir / "motif_summary.md"
    manifest_path = args.outdir / "motif_results.sha256"
    write_tsv(replicate_path, replicate_fields, replicate_rows)
    write_tsv(fimo_path, fimo_fields, fimo_rows)
    site_rows = [
        {
            "gene_id": gene,
            "matrix_id": motif,
            "window_bp": window,
            "fimo_p_threshold": fimo_threshold,
            "site_present": candidate_site_presence.get((motif, window, gene), False),
        }
        for window in windows
        for gene in candidate_genes_by_window.get(window, [])
        for motif in motif_ids
    ]
    write_tsv(
        candidate_site_path,
        ["gene_id", "matrix_id", "window_bp", "fimo_p_threshold", "site_present"],
        site_rows,
    )
    generated.extend([replicate_path, fimo_path, candidate_site_path, robust_path, summary_path])

    by_ame: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    by_fimo: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in replicate_rows:
        by_ame[(str(row["matrix_id"]), int(row["window_bp"]))].append(row)
    for row in fimo_rows:
        by_fimo[(str(row["matrix_id"]), int(row["window_bp"]))].append(row)
    robust_rows = []
    for motif in motif_ids:
        mapping = tf_map[motif]
        window_ame_counts = {
            window: sum(str(row["ame_replicate_pass"]).lower() == "true" for row in by_ame[(motif, window)])
            for window in windows
        }
        window_fimo_counts = {
            window: sum(str(row["fimo_replicate_pass"]).lower() == "true" for row in by_fimo[(motif, window)])
            for window in windows
        }
        enrichment_pass = all(window_ame_counts[window] >= passing_min for window in windows)
        tf_gene = mapping["litchi_gene_id"]
        tf_genes = [gene for gene in tf_gene.split(";") if gene]
        tf_expressions = [group_expression.get(gene, math.nan) for gene in tf_genes]
        complete_mapping = mapping["mapping_status"] == "ALL_COMPONENTS_ONE_TO_ONE_RBH"
        tf_expression = min(tf_expressions) if tf_expressions and all(map(math.isfinite, tf_expressions)) else math.nan
        tf_status = (
            "EXPRESSED" if complete_mapping and math.isfinite(tf_expression) and tf_expression >= float(config["tf_median_normalized_count_min"])
            else "NOT_EXPRESSED" if complete_mapping and math.isfinite(tf_expression)
            else "NOT_TESTABLE_NO_COMPLETE_ONE_TO_ONE_RBH"
        )
        status = (
            "ROBUST_CANDIDATE_MOTIF" if enrichment_pass and tf_status == "EXPRESSED"
            else "ROBUST_ENRICHMENT_TF_NOT_EXPRESSED" if enrichment_pass and tf_status == "NOT_EXPRESSED"
            else "ROBUST_ENRICHMENT_TF_NOT_TESTABLE" if enrichment_pass
            else "NOT_ROBUST"
        )
        robust_rows.append({
            "matrix_id": motif, "motif_name": mapping["motif_name"],
            "tf_class": mapping["tf_class"], "tf_family": mapping["tf_family"],
            "litchi_tf_gene_id": tf_gene, "litchi_tf_max_group_median_normalized_count": tf_expression,
            "tf_expression_status": tf_status,
            **{f"ame_pass_count_{window}bp": window_ame_counts[window] for window in windows},
            **{f"fimo_pass_count_{window}bp": window_fimo_counts[window] for window in windows},
            "both_windows_ame_pass": enrichment_pass,
            "discovery_motif_status": status,
            "external_transport_status": "PENDING",
        })
    robust_fields = [
        "matrix_id", "motif_name", "tf_class", "tf_family", "litchi_tf_gene_id",
        "litchi_tf_max_group_median_normalized_count", "tf_expression_status",
        *[f"ame_pass_count_{window}bp" for window in windows],
        *[f"fimo_pass_count_{window}bp" for window in windows],
        "both_windows_ame_pass", "discovery_motif_status", "external_transport_status",
    ]
    write_tsv(robust_path, robust_fields, robust_rows)
    robust_count = sum(row["discovery_motif_status"] == "ROBUST_CANDIDATE_MOTIF" for row in robust_rows)
    summary_path.write_text("\n".join([
        "# Promoter motif analysis", "",
        f"- Frozen JASPAR motifs: {len(motif_ids)}",
        f"- Matched backgrounds per promoter window: {sets}",
        f"- Robust motifs passing both windows and cognate-TF expression: {robust_count}",
        "- AME is primary; FIMO site presence and STREME/Tomtom are sensitivities/candidate discovery.",
        "- No motif is described as functional, and external transport remains pending.", "",
    ]), encoding="utf-8")
    with manifest_path.open("w") as handle:
        inputs = [args.inputs / "motif_inputs.sha256", args.motifs, args.tf_map, args.normalized_counts,
                  args.metadata, args.decisions, args.config]
        for path in [*inputs, *sorted(set(generated))]:
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"motif enrichment: {robust_count} robust candidate motifs")


if __name__ == "__main__":
    main()
