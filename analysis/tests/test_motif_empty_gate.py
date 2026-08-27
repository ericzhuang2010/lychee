#!/usr/bin/env python3
"""Regression test for the prespecified, outcome-independent motif empty gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pysam


ROOT = Path(__file__).resolve().parents[2]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lychee_motif_gate_test_") as temporary:
        work = Path(temporary)
        genome = work / "genome.fa"
        genome.write_text(">chr1\n" + "ACGT" * 1250 + "\n")
        pysam.faidx(str(genome))
        gtf = work / "genes.gtf"
        gtf.write_text(
            'chr1\ttest\texon\t1001\t1200\t.\t+\t.\tgene_id "g1"; transcript_id "t1";\n'
        )
        canonical = work / "canonical.tsv"
        canonical.write_text(
            "gene_id\tcanonical_transcript_id\tcds_bases\trule\n"
            "g1\tt1\t200\tfixture\n"
        )
        frozen = work / "frozen.tsv"
        frozen.write_text("gene_id\n" "g1\n")
        normalized = work / "normalized.tsv"
        normalized.write_text("gene_id\ts1\ts2\ts3\ts4\n" "g1\t20\t22\t18\t24\n")
        gene_qc = work / "gene_qc.tsv"
        gene_qc.write_text("gene_id\tuniform_gene_qc_status\n" "g1\tPASS\n")
        metadata = work / "metadata.tsv"
        metadata.write_text(
            "sample_id\tcultivar\ttreatment\n"
            "s1\tGuiwei\tmock\n"
            "s2\tGuiwei\tinfected\n"
            "s3\tYurong1\tmock\n"
            "s4\tYurong1\tinfected\n"
        )
        decisions = work / "decisions.tsv"
        decisions.write_text(
            "sample_id\tprimary_status\n"
            "s1\tINCLUDE\n" "s2\tINCLUDE\n" "s3\tINCLUDE\n" "s4\tINCLUDE\n"
        )
        config = work / "config.json"
        config.write_text(json.dumps({"motifs": {
            "promoter_windows_bp": [1000, 2000],
            "matched_background_sets": 100,
            "minimum_frozen_genes": 3,
            "seed": 20260718,
            "replicate_bh_q_max": 0.05,
            "minimum_odds_ratio": 1.5,
            "minimum_passing_backgrounds": 80,
            "fimo_p_threshold": 1e-4,
            "ame_evalue_report_threshold": 1e6,
            "streme_max_motifs": 10,
            "streme_min_width": 6,
            "streme_max_width": 20,
            "streme_p_threshold": 0.05,
            "tomtom_q_threshold": 0.05,
            "tf_median_normalized_count_min": 10,
        }}))
        motifs = work / "motifs.meme"
        motifs.write_text("MEME version 4\n\nALPHABET= ACGT\n\nMOTIF M1 fixture\n")
        tf_map = work / "tf_map.tsv"
        tf_map.write_text(
            "matrix_id\tmotif_name\ttf_class\ttf_family\tlitchi_gene_id\tmapping_status\n"
            "M1\tfixture\tfixture\tfixture\t\tNO_ONE_TO_ONE_RBH\n"
        )
        inputs = work / "inputs"
        results = work / "results"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/26_prepare_motif_inputs.py"),
            "--frozen-genes", str(frozen), "--normalized-counts", str(normalized),
            "--gene-qc", str(gene_qc), "--canonical", str(canonical),
            "--gtf", str(gtf), "--genome", str(genome), "--config", str(config),
            "--outdir", str(inputs),
        ], check=True)
        gate = rows(inputs / "motif_gate.tsv")
        assert len(gate) == 2
        assert {row["motif_gate_status"] for row in gate} == {"NOT_TESTABLE"}
        assert all(int(row["valid_candidate_promoters"]) == 1 for row in gate)

        nonexistent = work / "must_not_be_invoked"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/28_motif_enrichment.py"),
            "--inputs", str(inputs), "--motifs", str(motifs), "--tf-map", str(tf_map),
            "--normalized-counts", str(normalized), "--metadata", str(metadata),
            "--decisions", str(decisions), "--config", str(config), "--outdir", str(results),
            "--ame", str(nonexistent), "--fimo", str(nonexistent),
            "--streme", str(nonexistent), "--tomtom", str(nonexistent),
        ], check=True)
        robust = rows(results / "robust_candidate_motifs.tsv")
        assert len(robust) == 1
        assert robust[0]["discovery_motif_status"] == "NOT_ROBUST"
        assert robust[0]["tf_expression_status"] == "NOT_TESTABLE_NO_COMPLETE_ONE_TO_ONE_RBH"
        assert rows(results / "ame_matched_background_replicates.tsv") == []
        subprocess.run(["sha256sum", "-c", str(inputs / "motif_inputs.sha256")], check=True)
        subprocess.run(["sha256sum", "-c", str(results / "motif_results.sha256")], check=True)
    print("motif empty-gate synthetic test PASS")


if __name__ == "__main__":
    main()
