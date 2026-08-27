#!/usr/bin/env python3
"""Extract frozen-candidate proteins and add reviewed sequence/orthology evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import subprocess
import tempfile
from pathlib import Path


HIT_FIELDS = (
    "transcript_id", "subject_id", "percent_identity", "alignment_length",
    "qstart", "qend", "sstart", "send", "evalue", "bitscore", "query_length",
    "subject_length", "subject_title",
)
DIAMOND_FIELDS = (
    "qseqid", "sseqid", "pident", "length", "qstart", "qend", "sstart", "send",
    "evalue", "bitscore", "qlen", "slen", "stitle",
)


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def read_selected_fasta(path: Path, selected: set[str]) -> dict[str, str]:
    sequences: dict[str, str] = {}
    current: str | None = None
    chunks: list[str] = []
    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current in selected:
                    sequences[current] = "".join(chunks).rstrip("*.").upper()
                current = line[1:].split()[0]
                chunks = []
            elif current in selected:
                chunks.append(line)
        if current in selected:
            sequences[current] = "".join(chunks).rstrip("*.").upper()
    return sequences


def accession(subject_id: str) -> str:
    parts = subject_id.split("|")
    return parts[1] if len(parts) >= 3 else subject_id


def description(title: str) -> str:
    if " " in title:
        title = title.split(" ", 1)[1]
    return title.split(" OS=", 1)[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-genes", required=True, type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--proteins", required=True, type=Path)
    parser.add_argument("--swissprot-db", required=True, type=Path)
    parser.add_argument("--rice-rbh", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--diamond", default="diamond")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()

    frozen_rows = read_tsv(args.frozen_genes)
    if frozen_rows and "gene_id" not in frozen_rows[0]:
        raise ValueError("frozen gene table lacks gene_id")
    genes = sorted({row["gene_id"] for row in frozen_rows})

    canonical_rows = read_tsv(args.canonical)
    canonical = {row["gene_id"]: row for row in canonical_rows}
    missing = sorted(set(genes) - set(canonical))
    if missing:
        raise ValueError(f"frozen genes missing canonical transcript: {missing[:10]}")
    transcript_to_gene = {
        canonical[gene]["canonical_transcript_id"]: gene for gene in genes
    }
    sequences = read_selected_fasta(args.proteins, set(transcript_to_gene))
    missing_sequences = sorted(set(transcript_to_gene) - set(sequences))
    if missing_sequences:
        raise ValueError(f"canonical proteins missing from FASTA: {missing_sequences[:10]}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    fasta_path = args.outdir / "frozen_candidate_proteins.faa"
    selection_path = args.outdir / "representative_proteins.tsv"
    hit_path = args.outdir / "reviewed_swissprot_hits.tsv"
    evidence_path = args.outdir / "candidate_annotation_evidence.tsv"
    summary_path = args.outdir / "annotation_summary.md"
    manifest_path = args.outdir / "annotation_results.sha256"

    selection_rows: list[dict[str, object]] = []
    with fasta_path.open("w") as handle:
        for transcript, gene in sorted(transcript_to_gene.items(), key=lambda item: item[1]):
            sequence = sequences[transcript]
            handle.write(f">{transcript} gene={gene}\n")
            for start in range(0, len(sequence), 80):
                handle.write(sequence[start:start + 80] + "\n")
            selection_rows.append({
                "gene_id": gene,
                "canonical_transcript_id": transcript,
                "protein_length": len(sequence),
                "protein_md5": hashlib.md5(sequence.encode()).hexdigest(),
                "selection_rule": canonical[gene].get(
                    "rule", "longest_CDS_then_lexicographic_transcript_ID"
                ),
            })
    write_tsv(
        selection_path,
        ["gene_id", "canonical_transcript_id", "protein_length", "protein_md5", "selection_rule"],
        selection_rows,
    )

    hits: list[dict[str, object]] = []
    if genes:
        with tempfile.TemporaryDirectory(prefix="lychee_swissprot_") as tempdir:
            raw_path = Path(tempdir) / "hits.tsv"
            command = [
                args.diamond, "blastp", "--query", str(fasta_path), "--db", str(args.swissprot_db),
                "--out", str(raw_path), "--threads", str(args.threads), "--sensitive",
                "--max-target-seqs", "5", "--evalue", "1e-5", "--query-cover", "50",
                "--subject-cover", "50", "--outfmt", "6", *DIAMOND_FIELDS,
            ]
            subprocess.run(command, check=True)
            with raw_path.open() as handle:
                for raw in handle:
                    values = raw.rstrip("\n").split("\t", len(HIT_FIELDS) - 1)
                    if len(values) != len(HIT_FIELDS):
                        raise ValueError("malformed DIAMOND output")
                    row = dict(zip(HIT_FIELDS, values, strict=True))
                    qlen = int(row["query_length"])
                    slen = int(row["subject_length"])
                    aln = int(row["alignment_length"])
                    hits.append({
                        **row,
                        "gene_id": transcript_to_gene[row["transcript_id"]],
                        "swissprot_accession": accession(row["subject_id"]),
                        "swissprot_description": description(row["subject_title"]),
                        "query_coverage": aln / qlen,
                        "subject_coverage": aln / slen,
                    })
    hit_fields = [
        "gene_id", "transcript_id", "swissprot_accession", "swissprot_description",
        "percent_identity", "alignment_length", "query_length", "subject_length",
        "query_coverage", "subject_coverage", "evalue", "bitscore", "subject_id", "subject_title",
    ]
    write_tsv(hit_path, hit_fields, hits)

    best_hits: dict[str, dict[str, object]] = {}
    for hit in sorted(hits, key=lambda row: (-float(row["bitscore"]), str(row["subject_id"]))):
        best_hits.setdefault(str(hit["gene_id"]), hit)
    rice = {row["gene_id"]: row for row in read_tsv(args.rice_rbh)}

    evidence_rows: list[dict[str, object]] = []
    for selection in selection_rows:
        gene = str(selection["gene_id"])
        hit = best_hits.get(gene)
        ortholog = rice.get(gene)
        swiss_pass = hit is not None and float(hit["query_coverage"]) >= 0.70
        rice_pass = ortholog is not None and float(ortholog["query_coverage"]) >= 0.70
        classes = int(swiss_pass) + int(rice_pass)
        if classes >= 2:
            status = "PROVISIONAL_TWO_SEQUENCE_CLASSES_INTERPRO_PENDING"
        elif classes == 1:
            status = "FAMILY_LEVEL_SEQUENCE_SUPPORT_INTERPRO_PENDING"
        else:
            status = "UNANNOTATED_INTERPRO_PENDING"
        evidence_rows.append({
            **selection,
            "swissprot_accession": hit["swissprot_accession"] if hit else "",
            "swissprot_description": hit["swissprot_description"] if hit else "",
            "swissprot_percent_identity": hit["percent_identity"] if hit else "",
            "swissprot_query_coverage": hit["query_coverage"] if hit else "",
            "swissprot_subject_coverage": hit["subject_coverage"] if hit else "",
            "swissprot_evalue": hit["evalue"] if hit else "",
            "rice_ortholog_accession": ortholog["oryza_uniprot_accession"] if ortholog else "",
            "rice_query_coverage": ortholog["query_coverage"] if ortholog else "",
            "rice_subject_coverage": ortholog["subject_coverage"] if ortholog else "",
            "sequence_evidence_classes_70pct": classes,
            "interpro_status": "PENDING_TARGETED_QUERY",
            "architecture_conflict": "NOT_EVALUATED",
            "annotation_status": status,
        })
    evidence_fields = [
        "gene_id", "canonical_transcript_id", "protein_length", "protein_md5", "selection_rule",
        "swissprot_accession", "swissprot_description", "swissprot_percent_identity",
        "swissprot_query_coverage", "swissprot_subject_coverage", "swissprot_evalue",
        "rice_ortholog_accession", "rice_query_coverage", "rice_subject_coverage",
        "sequence_evidence_classes_70pct", "interpro_status", "architecture_conflict",
        "annotation_status",
    ]
    write_tsv(evidence_path, evidence_fields, evidence_rows)
    summary_path.write_text(
        "\n".join([
            "# Frozen-candidate sequence annotation",
            "",
            f"- Frozen genes: {len(genes)}",
            f"- Reviewed Swiss-Prot hits with >=70% query coverage: {sum(float(row['query_coverage']) >= 0.70 for row in best_hits.values())}",
            f"- One-to-one rice orthologs with >=70% query coverage: {sum(row['gene_id'] in rice and float(rice[row['gene_id']]['query_coverage']) >= 0.70 for row in selection_rows)}",
            "- High-confidence functional labels remain pending targeted InterPro/Pfam architecture checks.",
            "- Sequence-only evidence is not treated as functional validation.",
            "",
        ]),
        encoding="utf-8",
    )
    with manifest_path.open("w") as handle:
        for path in (
            args.frozen_genes, args.canonical, args.proteins, args.rice_rbh,
            fasta_path, selection_path, hit_path, evidence_path, summary_path,
        ):
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"candidate annotation: {len(genes)} genes, {len(hits)} reviewed Swiss-Prot hits")


if __name__ == "__main__":
    main()
