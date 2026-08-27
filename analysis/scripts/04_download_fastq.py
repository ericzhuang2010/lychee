#!/usr/bin/env python3
"""Download one study's paired ENA FASTQs sequentially and verify MD5/gzip.

An existing file with the wrong checksum is quarantined before retrying.  Passing
the ENA checksum to aria2 also makes transfer corruption fail at the downloader
instead of only at the post-download gate.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_gzip(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        for _ in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--minimum-free-bytes", type=int, default=161061273600)
    parser.add_argument("--connections", type=int, default=4)
    parser.add_argument(
        "--sample-id",
        help="Download exactly one sample (used by the staged external workflow)",
    )
    parser.add_argument(
        "--marker",
        help="Optional completion marker; defaults to OUTDIR/.download_complete",
    )
    parser.add_argument(
        "--name-by-sample",
        action="store_true",
        help="Name files SAMPLE_ID_R1/R2.fastq.gz instead of RUN_1/2.fastq.gz",
    )
    args = parser.parse_args()

    samples_path = ROOT / args.samples
    outdir = ROOT / args.outdir
    report = ROOT / args.report
    outdir.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    free_bytes = shutil.disk_usage(ROOT).free
    if free_bytes < args.minimum_free_bytes:
        raise RuntimeError(
            f"Free disk {free_bytes} is below preregistered minimum {args.minimum_free_bytes}"
        )
    aria2c = shutil.which("aria2c")
    sibling = Path(os.environ.get("CONDA_PREFIX", "")) / "bin" / "aria2c"
    if not aria2c and sibling.is_file():
        aria2c = str(sibling)
    if not aria2c:
        raise RuntimeError("aria2c is required")

    records: list[dict[str, str]] = []
    with samples_path.open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if args.sample_id:
        rows = [row for row in rows if row["sample_id"] == args.sample_id]
        if len(rows) != 1:
            raise ValueError(f"Expected one row for sample {args.sample_id}, observed {len(rows)}")
    for row in rows:
        urls = row["fastq_ftp"].split(";")
        checksums = row["fastq_md5"].split(";")
        if row["library_layout"] != "PAIRED" or len(urls) != 2 or len(checksums) != 2:
            raise ValueError(f"{row['sample_id']}: expected exactly two paired FASTQs")
        for mate, (url, expected_md5) in enumerate(zip(urls, checksums), 1):
            url = url if "://" in url else "https://" + url
            if args.name_by_sample:
                destination = outdir / f"{row['sample_id']}_R{mate}.fastq.gz"
            else:
                destination = outdir / f"{row['run']}_{mate}.fastq.gz"
            status = "REUSED"
            if destination.is_file():
                existing_md5 = md5(destination)
                if existing_md5 != expected_md5:
                    quarantine = destination.with_name(
                        f"{destination.name}.invalid-{existing_md5[:12]}"
                    )
                    suffix = 1
                    while quarantine.exists():
                        quarantine = destination.with_name(
                            f"{destination.name}.invalid-{existing_md5[:12]}-{suffix}"
                        )
                        suffix += 1
                    destination.replace(quarantine)
                    status = f"RETRIED_AFTER_QUARANTINE:{quarantine.name}"
            if not destination.is_file():
                subprocess.run(
                    [
                        aria2c, "--continue=true", "--allow-overwrite=true",
                        "--auto-file-renaming=false", "--check-certificate=true",
                        f"--checksum=md5={expected_md5}", "--max-tries=8",
                        "--retry-wait=10", "--file-allocation=none",
                        f"--max-connection-per-server={args.connections}",
                        f"--split={args.connections}", "--min-split-size=20M",
                        "--dir", str(outdir), "--out", destination.name, url,
                    ],
                    check=True,
                )
                if status == "REUSED":
                    status = "DOWNLOADED"
            observed_md5 = md5(destination)
            if observed_md5 != expected_md5:
                raise ValueError(
                    f"{destination}: MD5 {observed_md5} != expected {expected_md5}"
                )
            validate_gzip(destination)
            records.append(
                {
                    "sample_id": row["sample_id"], "run": row["run"],
                    "mate": str(mate), "path": str(destination.relative_to(ROOT)),
                    "bytes": str(destination.stat().st_size), "expected_md5": expected_md5,
                    "observed_md5": observed_md5, "status": status,
                }
            )

    temporary = report.with_suffix(report.suffix + ".tmp")
    with temporary.open("w") as handle:
        columns = ["sample_id", "run", "mate", "path", "bytes", "expected_md5", "observed_md5", "status"]
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    temporary.replace(report)
    marker = ROOT / args.marker if args.marker else outdir / ".download_complete"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("MD5 and gzip validation PASS\n")


if __name__ == "__main__":
    main()
