#!/usr/bin/env python3
"""Apply the preregistered post-verification large-intermediate cleanup."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_STUDIES = {"PRJNA830488", "PRJNA450886", "PRJNA922966", "PRJNA1090613"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_inside_root(path: Path) -> None:
    resolved = path.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise ValueError(f"Refusing cleanup outside project: {resolved}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True)
    parser.add_argument("--matrix-manifest", required=True)
    parser.add_argument("--qc-report", required=True)
    parser.add_argument("--completion-manifest", required=True)
    parser.add_argument("--log", default="analysis/logs/storage_cleanup.tsv")
    args = parser.parse_args()
    if args.study not in ALLOWED_STUDIES:
        raise ValueError(f"Study is not in the frozen registry: {args.study}")

    matrix_manifest = ROOT / args.matrix_manifest
    qc_report = ROOT / args.qc_report
    completion_manifest = ROOT / args.completion_manifest
    for path in (matrix_manifest, qc_report, completion_manifest):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Cleanup verification artifact missing: {path}")
    subprocess.run(
        ["sha256sum", "-c", str(matrix_manifest.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["sha256sum", "-c", str(completion_manifest.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
    )

    active_parent = "active_discovery" if args.study == "PRJNA830488" else "active_external"
    raw = ROOT / "data" / active_parent / args.study / "fastq"
    trimmed = ROOT / "data" / active_parent / args.study / "trimmed"
    alignment = ROOT / "results" / "alignment" / args.study
    raw_fastqs = sorted(raw.glob("*.fastq.gz")) if raw.is_dir() else []

    download_reports: list[Path] = []
    study_report = ROOT / "results" / "audit" / f"{args.study}_fastq_download.tsv"
    study_report_dir = ROOT / "results" / "audit" / f"{args.study}_fastq_download"
    if study_report.is_file():
        download_reports.append(study_report)
    if study_report_dir.is_dir():
        download_reports.extend(sorted(study_report_dir.glob("*.tsv")))
    if raw_fastqs and not download_reports:
        raise FileNotFoundError(
            f"Refusing raw FASTQ cleanup without download audit: {args.study}"
        )

    download_records: dict[str, dict[str, str]] = {}
    for report_path in download_reports:
        with report_path.open() as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("path"):
                    download_records[row["path"]] = row
    for fastq in raw_fastqs:
        relative = str(fastq.relative_to(ROOT))
        record = download_records.get(relative)
        if record is None:
            raise ValueError(f"No download-audit row for raw FASTQ: {relative}")
        expected = record.get("expected_md5", "")
        if not expected or record.get("observed_md5") != expected:
            raise ValueError(f"Download audit does not record MD5 PASS: {relative}")
        if int(record.get("bytes", "-1")) != fastq.stat().st_size:
            raise ValueError(f"Raw FASTQ size changed after download audit: {relative}")
        observed = md5(fastq)
        if observed != expected:
            raise ValueError(
                f"Raw FASTQ MD5 changed after download audit: {relative} "
                f"({observed} != {expected})"
            )

    targets: list[Path] = []
    targets.extend(raw_fastqs)
    if trimmed.is_dir():
        targets.extend(path for path in trimmed.rglob("*") if path.is_file())
    if alignment.is_dir():
        targets.extend(alignment.rglob("*.bam"))
        targets.extend(alignment.rglob("*.bam.bai"))
        targets.extend(alignment.rglob("*STARtmp*"))
    targets = sorted(set(targets))
    removed_bytes = 0
    removed_files = 0
    removed_directories = 0
    raw_fastq_files_removed = 0
    raw_fastq_bytes_removed = 0
    raw_fastq_set = set(raw_fastqs)
    for target in targets:
        assert_inside_root(target)
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink() or target.is_file():
            target_bytes = target.stat().st_size
            removed_bytes += target_bytes
            if target in raw_fastq_set:
                raw_fastq_files_removed += 1
                raw_fastq_bytes_removed += target_bytes
            target.unlink()
            removed_files += 1
        elif target.is_dir():
            removed_bytes += sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
            shutil.rmtree(target)
            removed_directories += 1
    if trimmed.is_dir() and not any(trimmed.iterdir()):
        trimmed.rmdir()
        removed_directories += 1

    log = ROOT / args.log
    log.parent.mkdir(parents=True, exist_ok=True)
    exists = log.is_file()
    with log.open("a") as handle:
        columns = [
            "date_time", "study", "matrix_manifest", "matrix_manifest_sha256",
            "qc_report", "qc_report_sha256", "completion_manifest",
            "completion_manifest_sha256", "removed_files", "removed_directories",
            "removed_bytes", "raw_fastq_files_removed", "raw_fastq_bytes_removed",
            "raw_fastq_md5_reverified", "raw_fastq_retained", "redownload_source",
            "status",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "date_time": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                "study": args.study,
                "matrix_manifest": str(matrix_manifest.relative_to(ROOT)),
                "matrix_manifest_sha256": sha256(matrix_manifest),
                "qc_report": str(qc_report.relative_to(ROOT)),
                "qc_report_sha256": sha256(qc_report),
                "completion_manifest": str(completion_manifest.relative_to(ROOT)),
                "completion_manifest_sha256": sha256(completion_manifest),
                "removed_files": removed_files,
                "removed_directories": removed_directories,
                "removed_bytes": removed_bytes,
                "raw_fastq_files_removed": raw_fastq_files_removed,
                "raw_fastq_bytes_removed": raw_fastq_bytes_removed,
                "raw_fastq_md5_reverified": "yes" if raw_fastqs else "not_applicable",
                "raw_fastq_retained": "no" if raw_fastqs else "not_present",
                "redownload_source": f"ENA BioProject {args.study}",
                "status": "PASS",
            }
        )
    print(
        f"cleanup PASS for {args.study}: {removed_files} files, "
        f"{removed_directories} directories, {removed_bytes} bytes"
    )


if __name__ == "__main__":
    main()
