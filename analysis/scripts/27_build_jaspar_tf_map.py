#!/usr/bin/env python3
"""Map fixed JASPAR Plants motifs to litchi genes by one-to-one reciprocal protein hits."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
import subprocess
from collections import defaultdict
from pathlib import Path


FIELDS = (
    "query", "subject", "percent_identity", "alignment_length", "mismatches", "gap_opens",
    "query_start", "query_end", "subject_start", "subject_end", "evalue", "bitscore",
    "query_length", "subject_length",
)
DIAMOND_FIELDS = (
    "qseqid", "sseqid", "pident", "length", "mismatch", "gapopen", "qstart", "qend",
    "sstart", "send", "evalue", "bitscore", "qlen", "slen",
)


def fasta_records(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    name: str | None = None
    chunks: list[str] = []
    with opener(path, "rt") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).rstrip("*.")
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
        if name is not None:
            yield name, "".join(chunks).rstrip("*.")


def read_hits(path: Path) -> dict[str, dict[str, object]]:
    hits: dict[str, dict[str, object]] = {}
    with path.open() as handle:
        for raw in handle:
            values = raw.rstrip("\n").split("\t")
            if len(values) != len(FIELDS):
                raise ValueError(f"malformed DIAMOND row in {path}")
            row: dict[str, object] = dict(zip(FIELDS, values, strict=True))
            row["query_coverage"] = int(str(row["alignment_length"])) / int(str(row["query_length"]))
            row["subject_coverage"] = int(str(row["alignment_length"])) / int(str(row["subject_length"]))
            if str(row["query"]) in hits:
                raise ValueError("DIAMOND output has multiple retained targets; require max-target-seqs 1")
            hits[str(row["query"])] = row
    return hits


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motifs", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--swissprot", required=True, type=Path)
    parser.add_argument("--litchi-proteins", required=True, type=Path)
    parser.add_argument("--litchi-db", required=True, type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--diamond", default="diamond")
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()

    motif_ids = []
    with args.motifs.open() as handle:
        for raw in handle:
            if raw.startswith("MOTIF "):
                motif_ids.append(raw.split()[1])
    if not motif_ids or len(motif_ids) != len(set(motif_ids)):
        raise ValueError("fixed motif file has no motifs or duplicate IDs")

    with args.metadata.open(newline="") as handle:
        metadata_rows = [
            row for row in csv.DictReader(handle, delimiter="\t")
            if row["tax_group"] == "plants" and row["matrix_id"] in set(motif_ids)
        ]
    by_motif = {row["matrix_id"]: row for row in metadata_rows}
    if set(by_motif) != set(motif_ids):
        raise ValueError(f"JASPAR metadata missing fixed motifs: {sorted(set(motif_ids) - set(by_motif))[:10]}")
    accessions = {
        accession
        for row in metadata_rows
        for accession in row["uniprot_ids"].split("::")
        if accession
    }

    sequences: dict[str, str] = {}
    for identifier, sequence in fasta_records(args.swissprot):
        parts = identifier.split("|")
        accession = parts[1] if len(parts) >= 3 else identifier
        if accession in accessions:
            sequences[accession] = sequence
    missing = sorted(accessions - set(sequences))

    args.outdir.mkdir(parents=True, exist_ok=True)
    tf_fasta = args.outdir / "jaspar2026_core_plants_tf.faa"
    tf_db = args.outdir / "jaspar2026_core_plants_tf.dmnd"
    forward_path = args.outdir / "litchi_to_jaspar_tf.tsv"
    reverse_path = args.outdir / "jaspar_tf_to_litchi.tsv"
    rbh_path = args.outdir / "jaspar_tf_one_to_one_rbh.tsv"
    mapping_path = args.outdir / "jaspar_motif_litchi_tf.tsv"
    qc_path = args.outdir / "jaspar_tf_mapping_qc.tsv"
    manifest_path = args.outdir / "jaspar_tf_mapping.sha256"

    with tf_fasta.open("w") as handle:
        for accession in sorted(sequences):
            handle.write(f">{accession}\n")
            for start in range(0, len(sequences[accession]), 80):
                handle.write(sequences[accession][start:start + 80] + "\n")
    subprocess.run([
        args.diamond, "makedb", "--in", str(tf_fasta), "--db", str(tf_db.with_suffix("")),
        "--threads", str(args.threads),
    ], check=True)
    common = [
        "--threads", str(args.threads), "--sensitive", "--max-target-seqs", "1",
        "--evalue", "1e-5", "--outfmt", "6", *DIAMOND_FIELDS,
    ]
    subprocess.run([
        args.diamond, "blastp", "--query", str(args.litchi_proteins), "--db", str(tf_db),
        "--out", str(forward_path), *common,
    ], check=True)
    subprocess.run([
        args.diamond, "blastp", "--query", str(tf_fasta), "--db", str(args.litchi_db),
        "--out", str(reverse_path), *common,
    ], check=True)

    canonical = {}
    with args.canonical.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            canonical[row["canonical_transcript_id"]] = row["gene_id"]
    forward = read_hits(forward_path)
    reverse = read_hits(reverse_path)
    retained = []
    for transcript, hit in forward.items():
        tf = str(hit["subject"])
        reciprocal = reverse.get(tf)
        if reciprocal is None or str(reciprocal["subject"]) != transcript:
            continue
        if (
            float(str(hit["evalue"])) > 1e-5
            or float(hit["query_coverage"]) < 0.70
            or float(hit["subject_coverage"]) < 0.70
            or float(str(reciprocal["evalue"])) > 1e-5
            or float(reciprocal["query_coverage"]) < 0.70
            or float(reciprocal["subject_coverage"]) < 0.70
        ):
            continue
        retained.append({
            "gene_id": canonical[transcript], "canonical_transcript_id": transcript,
            "jaspar_tf_uniprot_accession": tf, "percent_identity": hit["percent_identity"],
            "alignment_length": hit["alignment_length"], "query_length": hit["query_length"],
            "subject_length": hit["subject_length"], "query_coverage": hit["query_coverage"],
            "subject_coverage": hit["subject_coverage"], "evalue": hit["evalue"],
            "bitscore": hit["bitscore"],
        })
    gene_counts = defaultdict(int)
    tf_counts = defaultdict(int)
    for row in retained:
        gene_counts[row["gene_id"]] += 1
        tf_counts[row["jaspar_tf_uniprot_accession"]] += 1
    retained = [
        row for row in retained
        if gene_counts[row["gene_id"]] == 1 and tf_counts[row["jaspar_tf_uniprot_accession"]] == 1
    ]
    rbh_fields = [
        "gene_id", "canonical_transcript_id", "jaspar_tf_uniprot_accession", "percent_identity",
        "alignment_length", "query_length", "subject_length", "query_coverage",
        "subject_coverage", "evalue", "bitscore",
    ]
    with rbh_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rbh_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(sorted(retained, key=lambda row: row["gene_id"]))
    by_tf = {row["jaspar_tf_uniprot_accession"]: row for row in retained}
    mapping_fields = [
        "matrix_id", "motif_name", "tf_class", "tf_family", "source_tf_uniprot_accession",
        "source_species", "source_tax_id", "litchi_gene_id", "litchi_transcript_id",
        "percent_identity", "query_coverage", "subject_coverage", "mapping_status",
    ]
    mapping_rows = []
    for motif_id in motif_ids:
        metadata = by_motif[motif_id]
        component_accessions = [value for value in metadata["uniprot_ids"].split("::") if value]
        orthologs = [by_tf[value] for value in component_accessions if value in by_tf]
        all_components = bool(component_accessions) and len(orthologs) == len(component_accessions)
        mapping_status = (
            "ALL_COMPONENTS_ONE_TO_ONE_RBH" if all_components
            else "PARTIAL_COMPONENT_ONE_TO_ONE_RBH" if orthologs
            else "NO_ONE_TO_ONE_RBH"
        )
        mapping_rows.append({
            "matrix_id": motif_id, "motif_name": metadata["name"],
            "tf_class": metadata["class"], "tf_family": metadata["family"],
            "source_tf_uniprot_accession": metadata["uniprot_ids"], "source_species": metadata["species"],
            "source_tax_id": metadata["tax_id"],
            "litchi_gene_id": ";".join(str(row["gene_id"]) for row in orthologs),
            "litchi_transcript_id": ";".join(str(row["canonical_transcript_id"]) for row in orthologs),
            "percent_identity": ";".join(str(row["percent_identity"]) for row in orthologs),
            "query_coverage": ";".join(str(row["query_coverage"]) for row in orthologs),
            "subject_coverage": ";".join(str(row["subject_coverage"]) for row in orthologs),
            "mapping_status": mapping_status,
        })
    with mapping_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mapping_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(mapping_rows)

    qc_rows = [
        ("fixed_jaspar_plant_motifs", len(motif_ids), "PASS"),
        ("unique_jaspar_tf_accessions", len(accessions), "PASS"),
        ("tf_accessions_found_in_swissprot", len(sequences), "PASS" if not missing else "WARN"),
        ("tf_accessions_missing_from_swissprot", len(missing), "PASS" if not missing else "WARN"),
        ("one_to_one_rbh_tf_accessions", len(retained), "PASS"),
        ("motifs_with_complete_litchi_one_to_one_rbh", sum(row["mapping_status"] == "ALL_COMPONENTS_ONE_TO_ONE_RBH" for row in mapping_rows), "PASS"),
        ("motifs_with_partial_component_rbh", sum(row["mapping_status"] == "PARTIAL_COMPONENT_ONE_TO_ONE_RBH" for row in mapping_rows), "WARN"),
    ]
    with qc_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value", "status"]); writer.writerows(qc_rows)
        if missing:
            writer.writerow(["missing_accessions", ";".join(missing), "WARN"])
    with manifest_path.open("w") as handle:
        for path in (
            args.motifs, args.metadata, args.swissprot, args.litchi_proteins, args.litchi_db,
            args.canonical, tf_fasta, tf_db, forward_path, reverse_path, rbh_path, mapping_path, qc_path,
        ):
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"JASPAR TF map: {len(motif_ids)} motifs, {len(retained)} one-to-one litchi TF orthologs")


if __name__ == "__main__":
    main()
