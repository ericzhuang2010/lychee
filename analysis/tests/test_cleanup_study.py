#!/usr/bin/env python3
"""Regression test for fail-closed, MD5-verified staged cleanup."""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "analysis" / "scripts" / "22_cleanup_study.py"


def digest(path: Path, algorithm: str = "sha256") -> str:
    checksum = hashlib.new(algorithm)
    checksum.update(path.read_bytes())
    return checksum.hexdigest()


class CleanupStudyTest(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location("cleanup_study", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_verified_raw_trimmed_and_bam_are_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "data/active_external/PRJNA922966/fastq"
            trimmed = root / "data/active_external/PRJNA922966/trimmed"
            alignment = root / "results/alignment/PRJNA922966/sample"
            audit = root / "results/audit/PRJNA922966_fastq_download"
            external = root / "results/external/PRJNA922966"
            quantification = root / "results/quantification/PRJNA922966"
            for directory in (raw, trimmed, alignment, audit, external, quantification):
                directory.mkdir(parents=True, exist_ok=True)

            fastq = raw / "sample_R1.fastq.gz"
            with gzip.open(fastq, "wb") as handle:
                handle.write(b"@read\nACGT\n+\nIIII\n")
            trimmed_fastq = trimmed / "sample_R1.fastq.gz"
            trimmed_fastq.write_bytes(b"trimmed")
            bam = alignment / "Aligned.out.bam"
            bam.write_bytes(b"bam")

            report = audit / "sample.tsv"
            with report.open("w") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "sample_id", "run", "mate", "path", "bytes",
                        "expected_md5", "observed_md5", "status",
                    ],
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writeheader()
                md5 = digest(fastq, "md5")
                writer.writerow(
                    {
                        "sample_id": "sample",
                        "run": "run",
                        "mate": "1",
                        "path": str(fastq.relative_to(root)),
                        "bytes": fastq.stat().st_size,
                        "expected_md5": md5,
                        "observed_md5": md5,
                        "status": "DOWNLOADED",
                    }
                )

            matrix = quantification / "matrix.tsv"
            qc = root / "results/audit/PRJNA922966_technical_qc.tsv"
            completion = external / "result.tsv"
            matrix.write_text("matrix\n")
            qc.write_text("qc\n")
            completion.write_text("result\n")
            matrix_manifest = quantification / "matrix.sha256"
            completion_manifest = external / "external_results.sha256"
            matrix_manifest.write_text(
                f"{digest(matrix)}  {matrix.relative_to(root)}\n"
            )
            completion_manifest.write_text(
                f"{digest(completion)}  {completion.relative_to(root)}\n"
            )

            module = self.load_module()
            module.ROOT = root
            arguments = [
                str(SCRIPT),
                "--study", "PRJNA922966",
                "--matrix-manifest", str(matrix_manifest.relative_to(root)),
                "--qc-report", str(qc.relative_to(root)),
                "--completion-manifest", str(completion_manifest.relative_to(root)),
            ]
            with mock.patch.object(sys, "argv", arguments):
                module.main()

            self.assertFalse(fastq.exists())
            self.assertFalse(trimmed_fastq.exists())
            self.assertFalse(bam.exists())
            self.assertTrue(report.exists())
            log = root / "analysis/logs/storage_cleanup.tsv"
            with log.open() as handle:
                row = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(row["raw_fastq_md5_reverified"], "yes")
            self.assertEqual(row["raw_fastq_retained"], "no")
            self.assertEqual(row["raw_fastq_files_removed"], "1")

    def test_md5_mismatch_refuses_all_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "data/active_external/PRJNA922966/fastq"
            audit = root / "results/audit/PRJNA922966_fastq_download"
            external = root / "results/external/PRJNA922966"
            quantification = root / "results/quantification/PRJNA922966"
            for directory in (raw, audit, external, quantification):
                directory.mkdir(parents=True, exist_ok=True)
            fastq = raw / "sample_R1.fastq.gz"
            with gzip.open(fastq, "wb") as handle:
                handle.write(b"@read\nACGT\n+\nIIII\n")
            expected = "0" * 32
            report = audit / "sample.tsv"
            report.write_text(
                "sample_id\trun\tmate\tpath\tbytes\texpected_md5\tobserved_md5\tstatus\n"
                f"sample\trun\t1\t{fastq.relative_to(root)}\t{fastq.stat().st_size}\t"
                f"{expected}\t{expected}\tDOWNLOADED\n"
            )
            qc = root / "results/audit/qc.tsv"
            qc.write_text("qc\n")
            matrix_manifest = quantification / "matrix.sha256"
            completion_manifest = external / "external_results.sha256"
            matrix_manifest.write_text(f"{digest(qc)}  {qc.relative_to(root)}\n")
            completion_manifest.write_text(f"{digest(qc)}  {qc.relative_to(root)}\n")

            module = self.load_module()
            module.ROOT = root
            arguments = [
                str(SCRIPT), "--study", "PRJNA922966",
                "--matrix-manifest", str(matrix_manifest.relative_to(root)),
                "--qc-report", str(qc.relative_to(root)),
                "--completion-manifest", str(completion_manifest.relative_to(root)),
            ]
            with mock.patch.object(sys, "argv", arguments):
                with self.assertRaisesRegex(ValueError, "MD5 changed"):
                    module.main()
            self.assertTrue(fastq.exists())


if __name__ == "__main__":
    unittest.main()
