#!/usr/bin/env python3
"""Regression tests for external response selection and fail-closed motif transport."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lychee_external_motif_test_") as temporary:
        work = Path(temporary)
        config = work / "config.json"
        config.write_text(json.dumps({"motifs": {
            "promoter_windows_bp": [1000, 2000], "matched_background_sets": 100,
            "replicate_bh_q_max": 0.05, "minimum_odds_ratio": 1.5,
            "minimum_passing_backgrounds": 80, "fimo_p_threshold": 1e-4,
            "ame_evalue_report_threshold": 1e6,
            "external_transport": {
                "study": "PRJNA450886", "contrast": "primary_24h",
                "response_gene_bh_q_max": 0.05,
                "response_gene_absolute_log2fc_min": 0.5849625007211562,
                "minimum_response_genes": 3,
            },
        }}))
        contrasts = work / "contrasts.tsv"
        contrasts.write_text(
            "gene_id\tcontrast\texternal_log2fc\tgenomewide_q\n"
            "g1\tprimary_24h\t1.0\t0.001\n"
            "g2\tprimary_24h\t-1.2\t0.01\n"
            "g3\tprimary_24h\t0.7\t0.049\n"
            "g4\tprimary_24h\t0.2\t0.001\n"
        )
        response = work / "response"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/31_select_external_motif_genes.py"),
            "--all-contrasts", str(contrasts), "--config", str(config),
            "--study", "PRJNA450886", "--outdir", str(response),
        ], check=True)
        assert len(read_rows(response / "external_response_genes.tsv")) == 3
        assert read_rows(response / "external_response_gate.tsv")[0]["external_response_gate_status"] == "PASS"

        inputs = work / "inputs"
        inputs.mkdir()
        (inputs / "motif_inputs.sha256").write_text("fixture manifest\n")
        (inputs / "motif_gate.tsv").write_text(
            "window_bp\tmotif_gate_status\n1000\tNOT_TESTABLE\n2000\tNOT_TESTABLE\n"
        )
        discovery = work / "discovery.tsv"
        discovery.write_text(
            "matrix_id\tmotif_name\tdiscovery_motif_status\n"
            "M1\tfixture\tROBUST_CANDIDATE_MOTIF\n"
        )
        motifs = work / "motifs.meme"
        motifs.write_text(
            "MEME version 4\n\nALPHABET= ACGT\n\n"
            "MOTIF M1 fixture\nletter-probability matrix: alength= 4 w= 2 nsites= 1 E= 0\n"
            "0.25 0.25 0.25 0.25\n0.25 0.25 0.25 0.25\n"
        )
        output = work / "transport"
        nonexistent = work / "must_not_be_invoked"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/32_external_motif_transport.py"),
            "--inputs", str(inputs), "--response-gate", str(response / "external_response_gate.tsv"),
            "--discovery-motifs", str(discovery), "--motifs", str(motifs),
            "--config", str(config), "--outdir", str(output),
            "--ame", str(nonexistent), "--fimo", str(nonexistent),
        ], check=True)
        tests = read_rows(output / "external_motif_transport.tsv")
        assert len(tests) == 1
        assert tests[0]["external_motif_transport_status"] == "not_testable"
        assert read_rows(output / "external_ame_replicates.tsv") == []
        subprocess.run(["sha256sum", "-c", str(output / "external_motif_transport.sha256")], check=True)
    print("external motif empty-gate synthetic test PASS")


if __name__ == "__main__":
    main()
