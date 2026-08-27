#!/usr/bin/env python3
"""Combine frozen sequence and domain evidence into conservative annotation labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: str) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequence-evidence", required=True, type=Path)
    parser.add_argument("--interpro-summary", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text())["annotation"]
    coverage_min = float(config["minimum_query_coverage"])
    classes_min = int(config["high_confidence_minimum_classes"])
    sequence_rows = read_tsv(args.sequence_evidence)
    interpro_rows = read_tsv(args.interpro_summary)
    sequence = {row["gene_id"]: row for row in sequence_rows}
    interpro = {row["gene_id"]: row for row in interpro_rows}
    if len(sequence) != len(sequence_rows) or len(interpro) != len(interpro_rows):
        raise ValueError("duplicate gene IDs in candidate annotation inputs")
    if set(sequence) != set(interpro):
        raise ValueError("sequence and InterPro candidate gene sets differ")
    for gene in sequence:
        if sequence[gene].get("protein_md5", "").lower() != interpro[gene].get("protein_md5", "").lower():
            raise ValueError(f"protein MD5 differs between annotation layers for {gene}")

    fields = [
        "gene_id", "canonical_transcript_id", "protein_length", "protein_md5",
        "swissprot_accession", "swissprot_description", "swissprot_query_coverage",
        "rice_ortholog_accession", "rice_query_coverage", "pfam_accessions",
        "interpro_accessions", "architecture_union_coverage", "interpro_status",
        "swissprot_evidence_pass", "rice_rbh_evidence_pass",
        "interpro_pfam_evidence_pass", "annotation_evidence_classes",
        "annotation_evidence_class_count", "maximum_supported_sequence_coverage",
        "architecture_conflict_status", "high_confidence_annotation",
        "reported_function", "annotation_status", "annotation_failure",
    ]
    output_rows: list[dict[str, object]] = []
    for gene in sorted(sequence):
        seq = sequence[gene]
        domain = interpro[gene]
        swiss_cov = as_float(seq.get("swissprot_query_coverage", ""))
        rice_cov = as_float(seq.get("rice_query_coverage", ""))
        architecture_cov = as_float(domain.get("architecture_union_coverage", "")) or 0.0
        swiss_pass = swiss_cov is not None and swiss_cov >= coverage_min
        rice_pass = rice_cov is not None and rice_cov >= coverage_min
        interpro_pass = as_bool(domain.get("found", "")) and int(domain.get("match_count", "0")) > 0
        evidence = []
        if swiss_pass:
            evidence.append("reviewed Swiss-Prot DIAMOND match")
        if interpro_pass:
            evidence.append("InterPro/Pfam architecture")
        if rice_pass:
            evidence.append("one-to-one reciprocal-best Oryza ortholog")
        sequence_coverage = max(
            [value for value in (swiss_cov, rice_cov) if value is not None] or [0.0]
        )
        architecture_status = (
            "NO_CONFLICT_DETECTED_IN_DATABASE_MATCHES"
            if interpro_pass else "NOT_ASSESSABLE_NO_PRECOMPUTED_MATCH"
        )
        high_confidence = (
            len(evidence) >= classes_min
            and sequence_coverage >= coverage_min
            and architecture_status == "NO_CONFLICT_DETECTED_IN_DATABASE_MATCHES"
        )
        if seq.get("swissprot_description"):
            function = seq["swissprot_description"]
        elif domain.get("interpro_accessions"):
            function = "InterPro family " + domain["interpro_accessions"]
        elif domain.get("pfam_accessions"):
            function = "Pfam family " + domain["pfam_accessions"]
        elif seq.get("rice_ortholog_accession"):
            function = "family of Oryza ortholog " + seq["rice_ortholog_accession"]
        else:
            function = "unannotated protein"
        status = (
            "HIGH_CONFIDENCE_COMPUTATIONAL_FUNCTION"
            if high_confidence
            else "FAMILY_LEVEL_FUNCTION"
            if evidence
            else "UNANNOTATED"
        )
        output_rows.append({
            "gene_id": gene,
            "canonical_transcript_id": seq.get("canonical_transcript_id", ""),
            "protein_length": seq.get("protein_length", ""),
            "protein_md5": seq.get("protein_md5", ""),
            "swissprot_accession": seq.get("swissprot_accession", ""),
            "swissprot_description": seq.get("swissprot_description", ""),
            "swissprot_query_coverage": "" if swiss_cov is None else swiss_cov,
            "rice_ortholog_accession": seq.get("rice_ortholog_accession", ""),
            "rice_query_coverage": "" if rice_cov is None else rice_cov,
            "pfam_accessions": domain.get("pfam_accessions", ""),
            "interpro_accessions": domain.get("interpro_accessions", ""),
            "architecture_union_coverage": architecture_cov,
            "interpro_status": domain.get("interpro_status", ""),
            "swissprot_evidence_pass": swiss_pass,
            "rice_rbh_evidence_pass": rice_pass,
            "interpro_pfam_evidence_pass": interpro_pass,
            "annotation_evidence_classes": ";".join(evidence),
            "annotation_evidence_class_count": len(evidence),
            "maximum_supported_sequence_coverage": sequence_coverage,
            "architecture_conflict_status": architecture_status,
            "high_confidence_annotation": high_confidence,
            "reported_function": function,
            "annotation_status": status,
            "annotation_failure": False,
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    output = args.outdir / "final_candidate_annotations.tsv"
    summary = args.outdir / "final_annotation_summary.md"
    manifest = args.outdir / "final_annotation.sha256"
    write_tsv(output, fields, output_rows)
    summary.write_text("\n".join([
        "# Final frozen-candidate annotation", "",
        f"- Frozen candidate proteins: {len(output_rows)}.",
        f"- High-confidence computational functions: {sum(as_bool(str(row['high_confidence_annotation'])) for row in output_rows)}.",
        f"- Family-level functions: {sum(row['annotation_status'] == 'FAMILY_LEVEL_FUNCTION' for row in output_rows)}.",
        f"- Unannotated proteins: {sum(row['annotation_status'] == 'UNANNOTATED' for row in output_rows)}.",
        "- High confidence requires at least two frozen evidence classes, >=70% supported sequence coverage, and no conflict detected in available InterPro/Pfam matches.",
        "- No annotation is treated as experimental functional validation.", "",
    ]), encoding="utf-8")
    with manifest.open("w") as handle:
        for path in (args.sequence_evidence, args.interpro_summary, args.config, output, summary):
            handle.write(f"{sha256(path)}  {path}\n")
    print(
        f"final annotation: {len(output_rows)} candidates; "
        f"{sum(as_bool(str(row['high_confidence_annotation'])) for row in output_rows)} high confidence"
    )


if __name__ == "__main__":
    main()
