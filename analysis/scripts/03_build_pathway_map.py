#!/usr/bin/env python3
"""Freeze one-to-one reciprocal-best ortholog and Plant Reactome mappings."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def uniprot_accession(identifier: str) -> str:
    fields = identifier.split("|")
    return fields[1] if len(fields) >= 3 and fields[0] in {"sp", "tr"} else fields[0]


def read_canonical(path: Path) -> dict[str, str]:
    transcript_to_gene: dict[str, str] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            transcript_to_gene[row["canonical_transcript_id"]] = row["gene_id"]
    return transcript_to_gene


def read_hits(path: Path, rice_is_subject: bool) -> dict[str, dict[str, object]]:
    hits: dict[str, dict[str, object]] = {}
    with path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 11:
                raise ValueError(f"{path}:{line_number}: expected 11 DIAMOND columns")
            query, subject = fields[0], fields[1]
            if rice_is_subject:
                subject = uniprot_accession(subject)
            else:
                query = uniprot_accession(query)
            alignment_length, query_length, subject_length = map(int, fields[3:6])
            query_coverage = float(fields[6]) / 100
            subject_coverage = float(fields[7]) / 100
            if float(fields[8]) > 1e-5 or query_coverage < 0.70 or subject_coverage < 0.70:
                continue
            if query in hits:
                raise ValueError(
                    f"{path}: multiple retained targets for {query}; DIAMOND must use --max-target-seqs 1"
                )
            hits[query] = {
                "subject": subject,
                "identity": float(fields[2]),
                "alignment_length": alignment_length,
                "query_length": query_length,
                "subject_length": subject_length,
                "query_coverage": query_coverage,
                "subject_coverage": subject_coverage,
                "evalue": float(fields[8]),
                "bitscore": float(fields[9]),
                "mismatches": int(fields[10]),
            }
    return hits


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward", required=True)
    parser.add_argument("--reverse", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--pathways", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--minimum-size", type=int, default=10)
    parser.add_argument("--maximum-size", type=int, default=500)
    args = parser.parse_args()

    forward_path = ROOT / args.forward
    reverse_path = ROOT / args.reverse
    canonical_path = ROOT / args.canonical
    pathways_path = ROOT / args.pathways
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    transcript_to_gene = read_canonical(canonical_path)
    forward = read_hits(forward_path, rice_is_subject=True)
    reverse = read_hits(reverse_path, rice_is_subject=False)

    reciprocal: dict[str, tuple[str, dict[str, object]]] = {}
    for transcript, hit in forward.items():
        rice = str(hit["subject"])
        reverse_hit = reverse.get(rice)
        if (
            transcript in transcript_to_gene
            and reverse_hit is not None
            and reverse_hit["subject"] == transcript
        ):
            reciprocal[transcript] = (rice, hit)

    rice_to_transcripts: dict[str, list[str]] = defaultdict(list)
    gene_to_transcripts: dict[str, list[str]] = defaultdict(list)
    for transcript, (rice, _) in reciprocal.items():
        rice_to_transcripts[rice].append(transcript)
        gene_to_transcripts[transcript_to_gene[transcript]].append(transcript)

    # Enforce one-to-one at both reference-protein and litchi-gene levels.
    accepted = {
        transcript: value
        for transcript, value in reciprocal.items()
        if len(rice_to_transcripts[value[0]]) == 1
        and len(gene_to_transcripts[transcript_to_gene[transcript]]) == 1
    }

    ortholog_path = outdir / "one_to_one_rbh.tsv"
    with ortholog_path.open("w") as handle:
        columns = [
            "gene_id", "canonical_transcript_id", "oryza_uniprot_accession",
            "percent_identity", "alignment_length", "query_length", "subject_length",
            "query_coverage", "subject_coverage", "evalue", "bitscore", "mismatches",
        ]
        handle.write("\t".join(columns) + "\n")
        for transcript in sorted(accepted):
            rice, hit = accepted[transcript]
            values = [
                transcript_to_gene[transcript], transcript, rice,
                f'{hit["identity"]:.3f}', str(hit["alignment_length"]),
                str(hit["query_length"]), str(hit["subject_length"]),
                f'{hit["query_coverage"]:.6f}', f'{hit["subject_coverage"]:.6f}',
                f'{hit["evalue"]:.6g}', f'{hit["bitscore"]:.3f}', str(hit["mismatches"]),
            ]
            handle.write("\t".join(values) + "\n")

    rice_to_gene = {rice: transcript_to_gene[tx] for tx, (rice, _) in accepted.items()}
    pathway_names: dict[str, str] = {}
    pathway_genes: dict[str, set[str]] = defaultdict(set)
    with pathways_path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 4:
                raise ValueError(f"{pathways_path}:{line_number}: expected >=4 columns")
            pathway_id, pathway_name, species, member = fields[:4]
            if species != "Oryza sativa":
                continue
            pathway_names[pathway_id] = pathway_name
            gene = rice_to_gene.get(member)
            if gene:
                pathway_genes[pathway_id].add(gene)

    retained = {
        pathway_id: genes
        for pathway_id, genes in pathway_genes.items()
        if args.minimum_size <= len(genes) <= args.maximum_size
    }
    mapping_path = outdir / "plant_reactome_litchi.tsv"
    with mapping_path.open("w") as handle:
        handle.write("pathway_id\tpathway_name\tgene_id\n")
        for pathway_id in sorted(retained):
            for gene in sorted(retained[pathway_id]):
                handle.write(f"{pathway_id}\t{pathway_names[pathway_id]}\t{gene}\n")

    gmt_path = outdir / "plant_reactome_litchi.gmt"
    with gmt_path.open("w") as handle:
        for pathway_id in sorted(retained):
            label = f"{pathway_id}|{pathway_names[pathway_id]}"
            handle.write("\t".join([label, "Plant Reactome 2026-08-18", *sorted(retained[pathway_id])]) + "\n")

    qc_path = outdir / "pathway_mapping_qc.tsv"
    qc_rows = [
        ("canonical_litchi_proteins", len(transcript_to_gene)),
        ("forward_hits_passing_thresholds", len(forward)),
        ("reverse_hits_passing_thresholds", len(reverse)),
        ("reciprocal_best_transcript_pairs", len(reciprocal)),
        ("one_to_one_gene_pairs", len(accepted)),
        ("oryza_pathways_with_mapped_gene", len(pathway_genes)),
        ("retained_pathways_size_10_500", len(retained)),
    ]
    with qc_path.open("w") as handle:
        handle.write("metric\tvalue\n")
        for metric, value in qc_rows:
            handle.write(f"{metric}\t{value}\n")

    with (outdir / "pathway_mapping_checksums.sha256").open("w") as handle:
        for path in [forward_path, reverse_path, canonical_path, pathways_path, ortholog_path, mapping_path, gmt_path, qc_path]:
            handle.write(f"{sha256(path)}  {path.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
