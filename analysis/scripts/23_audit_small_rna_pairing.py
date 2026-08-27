#!/usr/bin/env python3
"""Audit whether GSE222650 small-RNA and GSE222651 mRNA libraries are specimen paired."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


KEYS = ("cultivar", "treatment", "time_h", "tissue", "replicate")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"sample_id", "biosample", "run", *KEYS}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path}: missing required columns or rows")
    return rows


def index_rows(rows: list[dict[str, str]], label: str) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in KEYS)
        if key in result:
            raise ValueError(f"duplicate {label} design key: {key}")
        result[key] = row
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--small-rna", required=True, type=Path)
    parser.add_argument("--mrna", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--checksums", required=True, type=Path)
    args = parser.parse_args()

    small = index_rows(read_rows(args.small_rna), "small-RNA")
    mrna = index_rows(read_rows(args.mrna), "mRNA")
    if set(small) != set(mrna):
        missing_mrna = sorted(set(small) - set(mrna))
        missing_small = sorted(set(mrna) - set(small))
        raise ValueError(
            f"design keys differ; missing mRNA={missing_mrna}, missing small-RNA={missing_small}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        *KEYS,
        "small_rna_sample_id", "small_rna_biosample", "small_rna_run",
        "mrna_sample_id", "mrna_biosample", "mrna_run", "pairing_status",
    ]
    same_biosample = 0
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for key in sorted(small):
            srna = small[key]
            messenger = mrna[key]
            shared = srna["biosample"] == messenger["biosample"]
            same_biosample += int(shared)
            writer.writerow({
                **dict(zip(KEYS, key, strict=True)),
                "small_rna_sample_id": srna["sample_id"],
                "small_rna_biosample": srna["biosample"],
                "small_rna_run": srna["run"],
                "mrna_sample_id": messenger["sample_id"],
                "mrna_biosample": messenger["biosample"],
                "mrna_run": messenger["run"],
                "pairing_status": (
                    "SAME_BIOSAMPLE" if shared else "DESIGN_MATCH_ONLY_NOT_SAME_BIOSAMPLE"
                ),
            })

    args.summary.write_text(
        "\n".join([
            "# GSE222650/GSE222651 pairing audit",
            "",
            f"- One-to-one design-cell matches: {len(small)}",
            f"- Shared BioSample accessions: {same_biosample}",
            "- The GEO titles match by cultivar, tissue, treatment, time, and replicate label.",
            "- Distinct BioSample accessions mean specimen pairing is not established.",
            "- Any integration must be labeled condition-level regulatory coherence, not specimen-level validation.",
            "",
        ]),
        encoding="utf-8",
    )
    with args.checksums.open("w") as handle:
        for path in (args.small_rna, args.mrna, args.output, args.summary):
            handle.write(f"{sha256(path)}  {path}\n")

    print(f"small-RNA pairing audit: {len(small)} design matches; {same_biosample} shared BioSamples")


if __name__ == "__main__":
    main()
