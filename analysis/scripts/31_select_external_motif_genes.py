#!/usr/bin/env python3
"""Select the outcome-blind, independently derived external motif response set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-contrasts", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--study", required=True)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())["motifs"]["external_transport"]
    if args.study != config["study"]:
        raise ValueError(f"external motif transport is frozen for {config['study']}, not {args.study}")
    with args.all_contrasts.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"gene_id", "contrast", "external_log2fc", "genomewide_q"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("external all-gene contrasts lack required fields")
    contrast_rows = [row for row in rows if row["contrast"] == config["contrast"]]
    if not contrast_rows:
        raise ValueError(f"frozen external motif contrast absent: {config['contrast']}")
    selected = []
    for row in contrast_rows:
        try:
            effect = float(row["external_log2fc"])
            q_value = float(row["genomewide_q"])
        except ValueError:
            continue
        if not (math.isfinite(effect) and math.isfinite(q_value)):
            continue
        if (
            q_value < float(config["response_gene_bh_q_max"])
            and abs(effect) >= float(config["response_gene_absolute_log2fc_min"])
        ):
            selected.append({
                "gene_id": row["gene_id"], "study": args.study,
                "contrast": row["contrast"], "external_log2fc": effect,
                "genomewide_q": q_value,
                "external_response_direction": "positive" if effect > 0 else "negative",
            })
    selected.sort(key=lambda row: (float(row["genomewide_q"]), str(row["gene_id"])))
    status = "PASS" if len(selected) >= int(config["minimum_response_genes"]) else "NOT_TESTABLE"
    reason = "minimum_external_response_genes_met" if status == "PASS" else "fewer_than_minimum_external_response_genes"
    args.outdir.mkdir(parents=True, exist_ok=True)
    genes = args.outdir / "external_response_genes.tsv"
    gate = args.outdir / "external_response_gate.tsv"
    summary = args.outdir / "external_response_summary.md"
    manifest = args.outdir / "external_response.sha256"
    fields = [
        "gene_id", "study", "contrast", "external_log2fc", "genomewide_q",
        "external_response_direction",
    ]
    with genes.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(selected)
    with gate.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "study", "contrast", "tested_genes", "selected_response_genes",
            "minimum_required", "external_response_gate_status", "reason",
        ])
        writer.writerow([
            args.study, config["contrast"], len(contrast_rows), len(selected),
            config["minimum_response_genes"], status, reason,
        ])
    summary.write_text("\n".join([
        "# External motif response set", "",
        f"- Study and contrast: {args.study} / {config['contrast']}.",
        f"- Genome-wide tested genes: {len(contrast_rows)}.",
        f"- Prespecified response genes: {len(selected)}.",
        f"- Motif response-set gate: **{status}**.",
        "- Selection is independent of discovery motif identities and discovery gene membership.", "",
    ]), encoding="utf-8")
    with manifest.open("w") as handle:
        for path in (args.all_contrasts, args.config, genes, gate, summary):
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"external motif response set: {len(selected)} genes; {status}")


if __name__ == "__main__":
    main()
