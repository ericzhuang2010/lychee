#!/usr/bin/env python3
"""Test discovery-frozen PWMs in an independently selected external response set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
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
                name, chunks = line[1:].split()[0], []
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
    positives, negatives, successes = tp + fn, fp + tn, tp + fp
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
    for rank in range(len(ordered), 0, -1):
        key = ordered[rank - 1]
        running = min(running, values[key] * len(ordered) / rank)
        result[key] = min(1.0, running)
    return result


def subset_meme(source: Path, destination: Path, motif_ids: list[str]) -> None:
    lines = source.read_text().splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("MOTIF ")]
    if not starts:
        raise ValueError("fixed MEME reference contains no motifs")
    found: set[str] = set()
    output = list(lines[:starts[0]])
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        motif = lines[start].split()[1]
        if motif in motif_ids:
            output.extend(lines[start:end]); found.add(motif)
    missing = set(motif_ids) - found
    if missing:
        raise ValueError(f"discovery-frozen motifs absent from reference: {sorted(missing)}")
    if not motif_ids:
        output.append("# No discovery motif passed the frozen robustness gate.\n")
    destination.write_text("".join(output))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--response-gate", required=True, type=Path)
    parser.add_argument("--discovery-motifs", required=True, type=Path)
    parser.add_argument("--motifs", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--ame", default="ame")
    parser.add_argument("--fimo", default="fimo")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())["motifs"]
    windows = sorted(map(int, config["promoter_windows_bp"]))
    sets = int(config["matched_background_sets"])
    q_max = float(config["replicate_bh_q_max"])
    or_min = float(config["minimum_odds_ratio"])
    passing_min = int(config["minimum_passing_backgrounds"])
    fimo_threshold = float(config["fimo_p_threshold"])
    response_gate = read_tsv(args.response_gate)
    if len(response_gate) != 1:
        raise ValueError("external response gate must contain exactly one row")
    promoter_gate = {int(row["window_bp"]): row for row in read_tsv(args.inputs / "motif_gate.tsv")}
    discovery = [
        row for row in read_tsv(args.discovery_motifs)
        if row["discovery_motif_status"] == "ROBUST_CANDIDATE_MOTIF"
    ]
    motif_ids = [row["matrix_id"] for row in discovery]
    motif_names = {row["matrix_id"]: row.get("motif_name", "") for row in discovery}
    if len(motif_ids) != len(set(motif_ids)):
        raise ValueError("duplicate discovery-frozen motif IDs")
    args.outdir.mkdir(parents=True, exist_ok=True)
    fixed_meme = args.outdir / "frozen_discovery_motifs.meme"
    subset_meme(args.motifs, fixed_meme, motif_ids)
    testable = (
        response_gate[0]["external_response_gate_status"] == "PASS"
        and all(promoter_gate[window]["motif_gate_status"] == "PASS" for window in windows)
        and bool(motif_ids)
    )

    ame_rows: list[dict[str, object]] = []
    fimo_rows: list[dict[str, object]] = []
    generated: list[Path] = [fixed_meme]
    if testable:
        for window in windows:
            primary_path = args.inputs / f"frozen_candidates_{window}bp.fa"
            primary = fasta_records(primary_path)
            for replicate in range(1, sets + 1):
                control_path = args.inputs / "backgrounds" / str(window) / f"replicate_{replicate:03d}.fa"
                control = fasta_records(control_path)
                raw_path = args.outdir / "ame_raw" / str(window) / f"replicate_{replicate:03d}.tsv"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                command = [
                    args.ame, "--verbose", "1", "--text", "--control", str(control_path),
                    "--method", "fisher", "--scoring", "totalhits", "--hit-lo-fraction", "0.25",
                    "--evalue-report-threshold", str(config["ame_evalue_report_threshold"]),
                    "--noseq", str(primary_path), str(fixed_meme),
                ]
                with raw_path.open("w") as handle:
                    subprocess.run(command, stdout=handle, check=True)
                generated.append(raw_path)
                seen: set[str] = set()
                for row in read_ame_tsv(raw_path):
                    motif = row["motif_ID"]
                    seen.add(motif)
                    tp, fp, pos, neg = int(row["TP"]), int(row["FP"]), int(row["pos"]), int(row["neg"])
                    ratio, q_value = odds_ratio(tp, pos - tp, fp, neg - fp), float(row["adj_p-value"])
                    ame_rows.append({
                        "window_bp": window, "replicate": replicate, "matrix_id": motif,
                        "motif_name": motif_names[motif], "ame_p": row["p-value"], "ame_q": q_value,
                        "ame_odds_ratio": ratio, "candidate_hits": tp, "candidate_total": pos,
                        "background_hits": fp, "background_total": neg,
                        "ame_replicate_pass": q_value < q_max and ratio >= or_min,
                    })
                for motif in set(motif_ids) - seen:
                    ame_rows.append({
                        "window_bp": window, "replicate": replicate, "matrix_id": motif,
                        "motif_name": motif_names[motif], "ame_p": 1.0, "ame_q": 1.0,
                        "ame_odds_ratio": 0.0, "candidate_hits": 0, "candidate_total": len(primary),
                        "background_hits": 0, "background_total": len(control),
                        "ame_replicate_pass": False,
                    })
                with tempfile.TemporaryDirectory(prefix="lychee_external_fimo_") as temporary:
                    combined = Path(temporary) / "combined.fa"
                    combined_fasta(combined, primary, control)
                    completed = subprocess.run([
                        args.fimo, "--text", "--skip-matched-sequence", "--thresh", str(fimo_threshold),
                        str(fixed_meme), str(combined),
                    ], check=True, capture_output=True, text=True)
                presence: dict[str, set[str]] = defaultdict(set)
                reader = csv.DictReader(
                    (line for line in completed.stdout.splitlines() if line and not line.startswith("#")),
                    delimiter="\t",
                )
                for row in reader:
                    presence[row["motif_id"]].add(row["sequence_name"])
                counts: dict[str, tuple[int, int, int, int]] = {}
                p_values: dict[str, float] = {}
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

    ame_fields = [
        "window_bp", "replicate", "matrix_id", "motif_name", "ame_p", "ame_q",
        "ame_odds_ratio", "candidate_hits", "candidate_total", "background_hits",
        "background_total", "ame_replicate_pass",
    ]
    fimo_fields = [
        "window_bp", "replicate", "matrix_id", "fimo_p", "fimo_q", "fimo_odds_ratio",
        "candidate_present", "candidate_total", "background_present", "background_total",
        "fimo_replicate_pass",
    ]
    ame_path = args.outdir / "external_ame_replicates.tsv"
    fimo_path = args.outdir / "external_fimo_sensitivity.tsv"
    status_path = args.outdir / "external_motif_transport.tsv"
    summary_path = args.outdir / "external_motif_transport_summary.md"
    manifest_path = args.outdir / "external_motif_transport.sha256"
    write_tsv(ame_path, ame_fields, ame_rows)
    write_tsv(fimo_path, fimo_fields, fimo_rows)
    by_ame: dict[tuple[str, int], int] = defaultdict(int)
    by_fimo: dict[tuple[str, int], int] = defaultdict(int)
    for row in ame_rows:
        by_ame[(str(row["matrix_id"]), int(row["window_bp"]))] += str(row["ame_replicate_pass"]).lower() == "true"
    for row in fimo_rows:
        by_fimo[(str(row["matrix_id"]), int(row["window_bp"]))] += str(row["fimo_replicate_pass"]).lower() == "true"
    status_rows = []
    for motif in motif_ids:
        ame_counts = {window: by_ame[(motif, window)] for window in windows}
        fimo_counts = {window: by_fimo[(motif, window)] for window in windows}
        status = (
            "cross_context_supported" if testable and all(ame_counts[window] >= passing_min for window in windows)
            else "unsupported" if testable else "not_testable"
        )
        status_rows.append({
            "matrix_id": motif, "motif_name": motif_names[motif],
            **{f"ame_pass_count_{window}bp": ame_counts[window] for window in windows},
            **{f"fimo_pass_count_{window}bp": fimo_counts[window] for window in windows},
            "external_motif_transport_status": status,
            "direct_replication": False,
        })
    status_fields = [
        "matrix_id", "motif_name", *[f"ame_pass_count_{window}bp" for window in windows],
        *[f"fimo_pass_count_{window}bp" for window in windows],
        "external_motif_transport_status", "direct_replication",
    ]
    write_tsv(status_path, status_fields, status_rows)
    supported = sum(row["external_motif_transport_status"] == "cross_context_supported" for row in status_rows)
    summary_path.write_text("\n".join([
        "# External candidate-motif transport", "",
        f"- Discovery-frozen robust PWMs: {len(motif_ids)}.",
        f"- External promoter gate testable: {str(testable).lower()}.",
        f"- Cross-context-supported candidate motifs: {supported}.",
        "- Only frozen PWMs were tested; no external motif rediscovery or retuning was run.",
        "- These are candidate motifs, not functional motifs or direct replication.", "",
    ]), encoding="utf-8")
    generated.extend([ame_path, fimo_path, status_path, summary_path])
    with manifest_path.open("w") as handle:
        inputs = [
            args.inputs / "motif_inputs.sha256", args.response_gate, args.discovery_motifs,
            args.motifs, args.config,
        ]
        for path in [*inputs, *sorted(set(generated))]:
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"external motif transport: {len(motif_ids)} frozen motifs; {supported} supported")


if __name__ == "__main__":
    main()
