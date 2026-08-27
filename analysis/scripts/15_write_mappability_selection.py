#!/usr/bin/env python3
"""Write a coordinate-sorted BED union of annotated exons for GenMap selection."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    intervals: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with Path(args.gtf).open() as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) == 9 and fields[2] == "exon":
                intervals[fields[0]].append((int(fields[3]) - 1, int(fields[4])))
    if not intervals:
        raise ValueError("No exon coordinates found")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    merged_count = 0
    merged_bases = 0
    with output.open("w") as handle:
        for sequence in sorted(intervals):
            merged: list[list[int]] = []
            for start, end in sorted(intervals[sequence]):
                if not merged or start > merged[-1][1]:
                    merged.append([start, end])
                elif end > merged[-1][1]:
                    merged[-1][1] = end
            for start, end in merged:
                handle.write(f"{sequence}\t{start}\t{end}\n")
                merged_count += 1
                merged_bases += end - start

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "metric\tvalue\n"
        f"host_sequences\t{len(intervals)}\n"
        f"merged_exon_intervals\t{merged_count}\n"
        f"merged_exon_bases\t{merged_bases}\n"
    )
    print(f"GenMap selection: {merged_count} intervals, {merged_bases} bases")


if __name__ == "__main__":
    main()
