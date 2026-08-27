#!/usr/bin/env python3
"""Convert featureCounts output into a validated integer gene-count matrix."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--featurecounts", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--counts", required=True)
    parser.add_argument("--annotation", required=True)
    args = parser.parse_args()

    with Path(args.samples).open() as handle:
        samples = list(csv.DictReader(handle, delimiter="\t"))
    sample_ids = [row["sample_id"] for row in samples]
    runs = [row["run"] for row in samples]
    if len(sample_ids) != len(set(sample_ids)) or len(runs) != len(set(runs)):
        raise ValueError("sample IDs and run accessions must be unique")

    with Path(args.featurecounts).open() as handle:
        reader = csv.reader((line for line in handle if not line.startswith("#")), delimiter="\t")
        header = next(reader)
        if header[:6] != ["Geneid", "Chr", "Start", "End", "Strand", "Length"]:
            raise ValueError("Unexpected featureCounts schema")
        bam_columns = header[6:]
        if len(bam_columns) != len(samples):
            raise ValueError("featureCounts BAM-column count does not match metadata")
        for bam, sample in zip(bam_columns, samples):
            if sample["sample_id"] not in bam:
                raise ValueError(f"BAM order mismatch: expected {sample['sample_id']} in {bam}")

        count_rows: list[list[str]] = []
        annotation_rows: list[list[str]] = []
        genes: set[str] = set()
        for row in reader:
            gene = row[0]
            if gene in genes:
                raise ValueError(f"Duplicate gene ID in featureCounts: {gene}")
            genes.add(gene)
            counts = row[6:]
            if any(not value.isdigit() for value in counts):
                raise ValueError(f"Noninteger count for {gene}")
            count_rows.append([gene, *counts])
            annotation_rows.append(row[:6])

    counts_path = Path(args.counts)
    annotation_path = Path(args.annotation)
    counts_path.parent.mkdir(parents=True, exist_ok=True)
    with counts_path.open("w") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene_id", *sample_ids])
        writer.writerows(count_rows)
    with annotation_path.open("w") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene_id", "chromosome", "start", "end", "strand", "length"])
        writer.writerows(annotation_rows)


if __name__ == "__main__":
    main()
