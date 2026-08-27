#!/usr/bin/env python3
"""Focused coordinate, overlap, and threshold test for gene mappability QC."""

from __future__ import annotations

import csv
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lychee_mappability_test_") as temporary:
        work = Path(temporary)
        gtf = work / "genes.gtf"
        bedgraph = work / "map.bedgraph"
        config = work / "config.json"
        output = work / "gene_qc.tsv"
        gtf.write_text(
            "chr1\ttest\texon\t1\t200\t.\t+\t.\tgene_id \"g1\"; transcript_id \"t1\";\n"
            "chr1\ttest\texon\t150\t260\t.\t+\t.\tgene_id \"g2\"; transcript_id \"t2\";\n"
            "chr1\ttest\texon\t300\t449\t.\t-\t.\tgene_id \"g3\"; transcript_id \"t3\";\n"
        )
        bedgraph.write_text(
            "chr1\t0\t180\t1\n"
            "chr1\t180\t260\t0.5\n"
            "chr1\t260\t449\t1\n"
        )
        config.write_text(json.dumps({
            "mappability": {
                "minimum_scored_exonic_bases": 100,
                "minimum_unique_exonic_fraction": 0.8,
                "unique_score": 1.0,
                "unique_score_tolerance": 1e-9,
            }
        }))
        subprocess.run([
            "python", str(ROOT / "analysis/scripts/10_gene_mappability.py"),
            "--gtf", str(gtf), "--bedgraph", str(bedgraph),
            "--config", str(config), "--output", str(output),
        ], check=True)
        with output.open() as handle:
            rows = {row["gene_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        assert rows["g1"]["mappability_status"] == "PASS"
        assert rows["g1"]["unique_gene_model_status"] == "FAIL"
        assert rows["g2"]["mappability_status"] == "FAIL"
        assert rows["g2"]["unique_gene_model_status"] == "FAIL"
        assert rows["g3"]["uniform_gene_qc_status"] == "PASS"
        assert float(rows["g3"]["fraction_unique_mappability"]) == 1.0
    print("gene mappability synthetic test PASS")


if __name__ == "__main__":
    main()
