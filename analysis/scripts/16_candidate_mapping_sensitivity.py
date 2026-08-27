#!/usr/bin/env python3
"""Measure coverage, mismatch, and multi-alignment bias for frozen genes."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import re
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


GENE_ID = re.compile(r'gene_id\s+["\']?([^;"\']+)')
CIGAR = re.compile(r"(\d+)([MIDNSHP=X])")


@dataclass(frozen=True)
class Interval:
    sequence: str
    start: int
    end: int
    gene: str


def merge(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[list[int]] = []
    for start, end in sorted(values):
        if not result or start > result[-1][1]:
            result.append([start, end])
        elif end > result[-1][1]:
            result[-1][1] = end
    return [(start, end) for start, end in result]


def candidate_intervals(gtf: Path, genes: set[str]) -> tuple[list[Interval], dict[str, int]]:
    raw: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    with gtf.open() as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            match = GENE_ID.search(fields[8])
            if match and match.group(1) in genes:
                raw[(fields[0], match.group(1))].append(
                    (int(fields[3]) - 1, int(fields[4]))
                )
    observed = {gene for _, gene in raw}
    if observed != genes:
        raise ValueError("Frozen genes missing from GTF: " + ",".join(sorted(genes - observed)))
    intervals: list[Interval] = []
    lengths: dict[str, int] = defaultdict(int)
    for (sequence, gene), values in raw.items():
        for start, end in merge(values):
            intervals.append(Interval(sequence, start, end, gene))
            lengths[gene] += end - start
    intervals.sort(key=lambda value: (value.sequence, value.start, value.end, value.gene))
    return intervals, dict(lengths)


def interval_index(intervals: list[Interval]):
    grouped: dict[str, list[Interval]] = defaultdict(list)
    for interval in intervals:
        grouped[interval.sequence].append(interval)
    starts = {
        sequence: [interval.start for interval in values]
        for sequence, values in grouped.items()
    }
    return grouped, starts


def genes_overlapping(
    sequence: str,
    start: int,
    end: int,
    grouped: dict[str, list[Interval]],
    starts: dict[str, list[int]],
) -> set[str]:
    if sequence not in grouped:
        return set()
    values = grouped[sequence]
    index = max(0, bisect.bisect_right(starts[sequence], start) - 1)
    genes: set[str] = set()
    while index < len(values) and values[index].start < end:
        interval = values[index]
        if interval.end > start:
            genes.add(interval.gene)
        index += 1
    return genes


def cigar_blocks(position: int, cigar: str) -> tuple[list[tuple[int, int]], int]:
    reference = position
    blocks: list[tuple[int, int]] = []
    aligned_bases = 0
    parsed = CIGAR.findall(cigar)
    if not parsed and cigar != "*":
        raise ValueError(f"Malformed CIGAR: {cigar}")
    for length_text, operation in parsed:
        length = int(length_text)
        if operation in {"M", "=", "X", "D"}:
            blocks.append((reference, reference + length))
            reference += length
        elif operation == "N":
            reference += length
        if operation in {"M", "=", "X", "I", "D"}:
            aligned_bases += length
    return blocks, aligned_bases


def write_rows(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-genes", required=True)
    parser.add_argument("--gtf", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--bam-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    samtools = shutil.which("samtools")
    if not samtools:
        raise RuntimeError("samtools is required")
    with Path(args.config).open() as handle:
        settings = json.load(handle)["mapping_sensitivity"]
    with Path(args.frozen_genes).open() as handle:
        frozen = list(csv.DictReader(handle, delimiter="\t"))
    genes = {row["gene_id"] for row in frozen}
    with Path(args.metadata).open() as handle:
        metadata = list(csv.DictReader(handle, delimiter="\t"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    bed = outdir / "candidate_exons.bed"
    sample_output = outdir / "candidate_mapping_per_sample.tsv"
    summary_output = outdir / "candidate_mapping_sensitivity.tsv"
    sample_columns = [
        "gene_id", "sample_id", "cultivar", "treatment", "union_exon_bases",
        "covered_exonic_bases", "exonic_coverage_breadth", "mean_exonic_depth",
        "overlapping_primary_alignments", "unique_alignments", "multi_alignments",
        "multi_alignment_fraction", "nm_events", "aligned_bases",
        "alignment_mismatch_rate",
    ]
    summary_columns = [
        "gene_id", "guiwei_alignments", "yurong1_alignments",
        "guiwei_mismatch_rate", "yurong1_mismatch_rate",
        "absolute_cultivar_mismatch_rate_difference", "cultivar_mismatch_rate_ratio",
        "higher_mismatch_cultivar", "guiwei_mean_coverage_breadth",
        "yurong1_mean_coverage_breadth", "breadth_loss_in_higher_mismatch_cultivar",
        "guiwei_multi_alignment_fraction", "yurong1_multi_alignment_fraction",
        "observed_bias_evaluable", "severe_composite_cultivar_bias",
        "severe_bilateral_multimapping", "observed_mapping_sensitivity_status",
    ]
    if not genes:
        bed.write_text("")
        write_rows(sample_output, sample_columns, [])
        write_rows(summary_output, summary_columns, [])
        print("No frozen genes; candidate mapping sensitivity is empty")
        return

    intervals, gene_lengths = candidate_intervals(Path(args.gtf), genes)
    with bed.open("w") as handle:
        for interval in intervals:
            handle.write(
                f"{interval.sequence}\t{interval.start}\t{interval.end}\t{interval.gene}\n"
            )
    grouped, starts = interval_index(intervals)

    sample_rows: list[dict[str, object]] = []
    for sample in metadata:
        sample_id = sample["sample_id"]
        bam = Path(args.bam_root) / sample_id / "Aligned.sortedByCoord.out.bam"
        if not bam.is_file():
            raise FileNotFoundError(bam)
        depth_sum: dict[str, int] = defaultdict(int)
        covered: dict[str, int] = defaultdict(int)
        depth_process = subprocess.Popen(
            [samtools, "depth", "-a", "-b", str(bed), str(bam)],
            stdout=subprocess.PIPE, text=True,
        )
        assert depth_process.stdout is not None
        for line in depth_process.stdout:
            sequence, position_text, depth_text = line.rstrip("\n").split("\t")[:3]
            position = int(position_text) - 1
            overlap = genes_overlapping(
                sequence, position, position + 1, grouped, starts
            )
            if len(overlap) != 1:
                continue
            gene = next(iter(overlap))
            depth = int(depth_text)
            depth_sum[gene] += depth
            if depth > 0:
                covered[gene] += 1
        if depth_process.wait() != 0:
            raise subprocess.CalledProcessError(depth_process.returncode, depth_process.args)

        alignments: dict[str, int] = defaultdict(int)
        unique_alignments: dict[str, int] = defaultdict(int)
        multi_alignments: dict[str, int] = defaultdict(int)
        nm_events: dict[str, int] = defaultdict(int)
        aligned_bases: dict[str, int] = defaultdict(int)
        view_process = subprocess.Popen(
            [samtools, "view", "-F", "0xF04", "-L", str(bed), str(bam)],
            stdout=subprocess.PIPE, text=True,
        )
        assert view_process.stdout is not None
        for line in view_process.stdout:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 11:
                continue
            sequence = fields[2]
            blocks, aligned = cigar_blocks(int(fields[3]) - 1, fields[5])
            overlapping: set[str] = set()
            for start, end in blocks:
                overlapping.update(genes_overlapping(sequence, start, end, grouped, starts))
            if len(overlapping) != 1:
                continue
            gene = next(iter(overlapping))
            tags = {tag.split(":", 2)[0]: tag.split(":", 2)[-1] for tag in fields[11:]}
            nh = int(tags.get("NH", "1"))
            nm = int(tags.get("NM", "0"))
            alignments[gene] += 1
            if nh == 1:
                unique_alignments[gene] += 1
            else:
                multi_alignments[gene] += 1
            nm_events[gene] += nm
            aligned_bases[gene] += aligned
        if view_process.wait() != 0:
            raise subprocess.CalledProcessError(view_process.returncode, view_process.args)

        for gene in sorted(genes):
            total = gene_lengths[gene]
            mapped = alignments.get(gene, 0)
            multi = multi_alignments.get(gene, 0)
            aligned = aligned_bases.get(gene, 0)
            sample_rows.append({
                "gene_id": gene,
                "sample_id": sample_id,
                "cultivar": sample["cultivar"],
                "treatment": sample["treatment"],
                "union_exon_bases": total,
                "covered_exonic_bases": covered.get(gene, 0),
                "exonic_coverage_breadth": covered.get(gene, 0) / total,
                "mean_exonic_depth": depth_sum.get(gene, 0) / total,
                "overlapping_primary_alignments": mapped,
                "unique_alignments": unique_alignments.get(gene, 0),
                "multi_alignments": multi,
                "multi_alignment_fraction": multi / mapped if mapped else 0.0,
                "nm_events": nm_events.get(gene, 0),
                "aligned_bases": aligned,
                "alignment_mismatch_rate": nm_events.get(gene, 0) / aligned if aligned else math.nan,
            })
    write_rows(sample_output, sample_columns, sample_rows)

    summary_rows: list[dict[str, object]] = []
    minimum_alignments = int(settings["minimum_alignments_per_cultivar_for_bias_call"])
    for gene in sorted(genes):
        values = [row for row in sample_rows if row["gene_id"] == gene]
        by_cultivar = {
            cultivar: [row for row in values if row["cultivar"] == cultivar]
            for cultivar in ("Guiwei", "Yurong1")
        }
        aggregate: dict[str, dict[str, float]] = {}
        for cultivar, rows in by_cultivar.items():
            align_count = sum(int(row["overlapping_primary_alignments"]) for row in rows)
            aligned = sum(int(row["aligned_bases"]) for row in rows)
            nm = sum(int(row["nm_events"]) for row in rows)
            multi = sum(int(row["multi_alignments"]) for row in rows)
            aggregate[cultivar] = {
                "alignments": align_count,
                "mismatch_rate": nm / aligned if aligned else math.nan,
                "breadth": sum(float(row["exonic_coverage_breadth"]) for row in rows) / len(rows),
                "multi_fraction": multi / align_count if align_count else 0.0,
            }
        guiwei, yurong = aggregate["Guiwei"], aggregate["Yurong1"]
        rates = [guiwei["mismatch_rate"], yurong["mismatch_rate"]]
        rates_finite = all(math.isfinite(value) for value in rates)
        difference = abs(rates[0] - rates[1]) if rates_finite else math.nan
        lower = min(rates) if rates_finite else math.nan
        ratio = max(rates) / lower if rates_finite and lower > 0 else (
            math.inf if rates_finite and max(rates) > 0 else math.nan
        )
        higher = (
            "Guiwei" if rates_finite and rates[0] >= rates[1]
            else "Yurong1" if rates_finite else "NA"
        )
        breadth_loss = (
            yurong["breadth"] - guiwei["breadth"]
            if higher == "Guiwei" else
            guiwei["breadth"] - yurong["breadth"]
            if higher == "Yurong1" else math.nan
        )
        evaluable = (
            guiwei["alignments"] >= minimum_alignments
            and yurong["alignments"] >= minimum_alignments
            and rates_finite
        )
        severe_composite = (
            evaluable
            and difference >= float(settings["minimum_absolute_cultivar_mismatch_rate_difference"])
            and ratio >= float(settings["minimum_cultivar_mismatch_rate_ratio"])
            and breadth_loss >= float(settings["minimum_breadth_loss_in_higher_mismatch_cultivar"])
        )
        severe_multi = (
            evaluable
            and guiwei["multi_fraction"] > float(settings["severe_multimapping_fraction"])
            and yurong["multi_fraction"] > float(settings["severe_multimapping_fraction"])
        )
        status = (
            "FAIL_SEVERE_COMPOSITE_CULTIVAR_BIAS" if severe_composite else
            "FAIL_SEVERE_BILATERAL_MULTIMAPPING" if severe_multi else
            "PASS_NO_SEVERE_OBSERVED_BIAS" if evaluable else
            "PASS_UNIFORM_MAPPABILITY_OBSERVED_LOW_COVERAGE"
        )
        summary_rows.append({
            "gene_id": gene,
            "guiwei_alignments": int(guiwei["alignments"]),
            "yurong1_alignments": int(yurong["alignments"]),
            "guiwei_mismatch_rate": guiwei["mismatch_rate"],
            "yurong1_mismatch_rate": yurong["mismatch_rate"],
            "absolute_cultivar_mismatch_rate_difference": difference,
            "cultivar_mismatch_rate_ratio": ratio,
            "higher_mismatch_cultivar": higher,
            "guiwei_mean_coverage_breadth": guiwei["breadth"],
            "yurong1_mean_coverage_breadth": yurong["breadth"],
            "breadth_loss_in_higher_mismatch_cultivar": breadth_loss,
            "guiwei_multi_alignment_fraction": guiwei["multi_fraction"],
            "yurong1_multi_alignment_fraction": yurong["multi_fraction"],
            "observed_bias_evaluable": evaluable,
            "severe_composite_cultivar_bias": severe_composite,
            "severe_bilateral_multimapping": severe_multi,
            "observed_mapping_sensitivity_status": status,
        })
    write_rows(summary_output, summary_columns, summary_rows)
    failures = sum(
        str(row["observed_mapping_sensitivity_status"]).startswith("FAIL")
        for row in summary_rows
    )
    print(f"candidate mapping sensitivity: {len(summary_rows)} genes, {failures} severe flags")


if __name__ == "__main__":
    main()
