#!/usr/bin/env python3
"""Merge one-BAM featureCounts outputs without retaining study-wide BAMs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ANNOTATION_COLUMNS = ["Geneid", "Chr", "Start", "End", "Strand", "Length"]


def read_counts(path: Path, sample_id: str) -> tuple[list[list[str]], list[list[str]]]:
    with path.open() as handle:
        reader = csv.reader((line for line in handle if not line.startswith("#")), delimiter="\t")
        header = next(reader)
        if header[:6] != ANNOTATION_COLUMNS or len(header) != 7:
            raise ValueError(f"Unexpected single-sample featureCounts schema: {path}")
        if sample_id not in header[6]:
            raise ValueError(f"Expected {sample_id} in BAM column {header[6]}")
        annotation: list[list[str]] = []
        values: list[list[str]] = []
        seen: set[str] = set()
        for row in reader:
            if len(row) != 7 or row[0] in seen or not row[6].isdigit():
                raise ValueError(f"Invalid featureCounts row in {path}: {row[:2]}")
            seen.add(row[0])
            annotation.append(row[:6])
            values.append([row[0], row[6]])
    return annotation, values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--counts", required=True)
    parser.add_argument("--annotation", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    with Path(args.samples).open() as handle:
        samples = list(csv.DictReader(handle, delimiter="\t"))
    if not samples:
        raise ValueError("Empty sample manifest")

    expected_annotation: list[list[str]] | None = None
    genes: list[str] | None = None
    sample_values: list[list[str]] = []
    summary_rows: list[dict[str, str]] = []
    for sample in samples:
        sample_id = sample["sample_id"]
        path = Path(args.input_dir) / f"{sample_id}.txt"
        annotation, values = read_counts(path, sample_id)
        if expected_annotation is None:
            expected_annotation = annotation
            genes = [row[0] for row in values]
        elif annotation != expected_annotation:
            raise ValueError(f"Gene annotation/order differs in {path}")
        sample_values.append([row[1] for row in values])

        summary_path = path.with_suffix(path.suffix + ".summary")
        with summary_path.open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None or len(reader.fieldnames) != 2:
                raise ValueError(f"Unexpected featureCounts summary: {summary_path}")
            count_column = reader.fieldnames[1]
            for row in reader:
                summary_rows.append(
                    {"sample_id": sample_id, "status": row["Status"], "read_pairs": row[count_column]}
                )

    assert genes is not None and expected_annotation is not None
    counts_path = Path(args.counts)
    annotation_path = Path(args.annotation)
    summary_path = Path(args.summary)
    for output in (counts_path, annotation_path, summary_path):
        output.parent.mkdir(parents=True, exist_ok=True)

    with counts_path.open("w") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene_id", *(row["sample_id"] for row in samples)])
        for index, gene in enumerate(genes):
            writer.writerow([gene, *(column[index] for column in sample_values)])
    with annotation_path.open("w") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene_id", "chromosome", "start", "end", "strand", "length"])
        writer.writerows(expected_annotation)
    with summary_path.open("w") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_id", "status", "read_pairs"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
