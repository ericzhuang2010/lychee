#!/usr/bin/env python3
"""Build and validate the frozen competitive host/pathogen reference.

The script deliberately uses only the Python standard library.  It fails closed
on contig, coordinate, identifier, hierarchy, or CDS/protein inconsistencies.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for token in raw.rstrip().split(";"):
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Malformed GFF3 attribute: {token!r}")
        key, value = token.split("=", 1)
        attrs[key] = value
    return attrs


def fasta_lengths(path: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    current: str | None = None
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                current = line[1:].split()[0]
                if current in lengths:
                    raise ValueError(f"Duplicate FASTA identifier {current} in {path}")
                lengths[current] = 0
            else:
                if current is None:
                    raise ValueError(f"Sequence precedes FASTA header in {path}")
                lengths[current] += len(line.strip())
    return lengths


def fasta_sequences(path: Path) -> dict[str, str]:
    sequences: dict[str, list[str]] = {}
    current: str | None = None
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                current = line[1:].split()[0]
                if current in sequences:
                    raise ValueError(f"Duplicate FASTA identifier {current} in {path}")
                sequences[current] = []
            else:
                if current is None:
                    raise ValueError(f"Sequence precedes FASTA header in {path}")
                sequences[current].append(line.strip().upper())
    return {identifier: "".join(parts) for identifier, parts in sequences.items()}


CODON_TABLE = {
    codon: amino_acid
    for amino_acid, codons in {
        "F": ("TTT", "TTC"), "L": ("TTA", "TTG", "CTT", "CTC", "CTA", "CTG"),
        "I": ("ATT", "ATC", "ATA"), "M": ("ATG",), "V": ("GTT", "GTC", "GTA", "GTG"),
        "S": ("TCT", "TCC", "TCA", "TCG", "AGT", "AGC"), "P": ("CCT", "CCC", "CCA", "CCG"),
        "T": ("ACT", "ACC", "ACA", "ACG"), "A": ("GCT", "GCC", "GCA", "GCG"),
        "Y": ("TAT", "TAC"), "*": ("TAA", "TAG", "TGA"), "H": ("CAT", "CAC"),
        "Q": ("CAA", "CAG"), "N": ("AAT", "AAC"), "K": ("AAA", "AAG"),
        "D": ("GAT", "GAC"), "E": ("GAA", "GAG"), "C": ("TGT", "TGC"),
        "W": ("TGG",), "R": ("CGT", "CGC", "CGA", "CGG", "AGA", "AGG"),
        "G": ("GGT", "GGC", "GGA", "GGG"),
    }.items()
    for codon in codons
}


def translate_dna(sequence: str) -> str:
    return "".join(
        CODON_TABLE.get(sequence[index : index + 3], "X")
        for index in range(0, len(sequence) - 2, 3)
    )


def copy_prefixed_fasta(source: Path, destination: Path, prefix: str) -> dict[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    lengths: dict[str, int] = {}
    current: str | None = None
    with open_text(source) as reader, destination.open("w") as writer:
        for line in reader:
            if line.startswith(">"):
                original = line[1:].rstrip()
                current = original.split()[0]
                if current in lengths:
                    raise ValueError(f"Duplicate FASTA identifier {current} in {source}")
                lengths[current] = 0
                suffix = original[len(current) :]
                writer.write(f">{prefix}{current}{suffix}\n")
            else:
                if current is None:
                    raise ValueError(f"Sequence precedes FASTA header in {source}")
                sequence = line.strip()
                lengths[current] += len(sequence)
                writer.write(sequence + "\n")
    return lengths


def parse_gff(
    path: Path, contigs: dict[str, int]
) -> tuple[dict[str, str], Counter, dict[str, int], set[str], int]:
    transcript_to_gene: dict[str, str] = {}
    gene_transcript_counts: Counter = Counter()
    cds_bases: dict[str, int] = defaultdict(int)
    feature_ids: set[str] = set()
    parent_ids: set[str] = set()
    n_features = 0

    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_number}: expected 9 columns")
            seqid, _, feature, start_raw, end_raw, _, _, _, raw_attrs = fields
            if seqid not in contigs:
                raise ValueError(f"{path}:{line_number}: unknown contig {seqid}")
            start, end = int(start_raw), int(end_raw)
            if start < 1 or end < start or end > contigs[seqid]:
                raise ValueError(
                    f"{path}:{line_number}: out-of-bounds coordinates "
                    f"{seqid}:{start}-{end} (length {contigs[seqid]})"
                )
            attrs = parse_attributes(raw_attrs)
            feature_id = attrs.get("ID")
            if feature_id:
                if feature_id in feature_ids:
                    raise ValueError(f"{path}:{line_number}: duplicate ID {feature_id}")
                feature_ids.add(feature_id)
            parents = attrs.get("Parent", "").split(",") if attrs.get("Parent") else []
            parent_ids.update(parents)
            if feature == "mRNA":
                transcript = attrs.get("ID")
                gene = attrs.get("geneID") or attrs.get("gene_name")
                if not transcript or not gene:
                    raise ValueError(f"{path}:{line_number}: mRNA lacks ID or geneID")
                if transcript in transcript_to_gene:
                    raise ValueError(f"{path}:{line_number}: duplicate transcript {transcript}")
                transcript_to_gene[transcript] = gene
                gene_transcript_counts[gene] += 1
            elif feature == "CDS":
                if not parents:
                    raise ValueError(f"{path}:{line_number}: CDS lacks Parent")
                for parent in parents:
                    cds_bases[parent] += end - start + 1
            n_features += 1

    missing_parents = sorted(parent_ids - feature_ids)
    if missing_parents:
        raise ValueError(
            "GFF3 hierarchy has unresolved Parent identifiers: "
            + ", ".join(missing_parents[:10])
        )
    if set(cds_bases) - set(transcript_to_gene):
        raise ValueError("CDS Parent identifiers do not resolve exclusively to mRNAs")
    return transcript_to_gene, gene_transcript_counts, dict(cds_bases), feature_ids, n_features


def write_annotations(
    source: Path,
    prefixed_gff: Path,
    gtf: Path,
    transcript_to_gene: dict[str, str],
) -> int:
    n_gtf_exons = 0
    with open_text(source) as reader, prefixed_gff.open("w") as gff_out, gtf.open("w") as gtf_out:
        gff_out.write("##gff-version 3\n")
        for line_number, line in enumerate(reader, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            fields[0] = "HOST_" + fields[0]
            gff_out.write("\t".join(fields) + "\n")
            if fields[2] != "exon":
                continue
            attrs = parse_attributes(fields[8])
            parents = attrs.get("Parent", "").split(",") if attrs.get("Parent") else []
            if not parents:
                raise ValueError(f"{source}:{line_number}: exon lacks Parent")
            for transcript in parents:
                if transcript not in transcript_to_gene:
                    raise ValueError(
                        f"{source}:{line_number}: exon Parent {transcript} is not an mRNA"
                    )
                gene = transcript_to_gene[transcript]
                gtf_fields = fields[:8] + [f'gene_id "{gene}"; transcript_id "{transcript}";']
                gtf_out.write("\t".join(gtf_fields) + "\n")
                n_gtf_exons += 1
    return n_gtf_exons


def write_tx2gene_and_canonical(
    outdir: Path,
    transcript_to_gene: dict[str, str],
    cds_bases: dict[str, int],
) -> None:
    tx2gene = outdir / "transcript_to_gene.tsv"
    with tx2gene.open("w") as handle:
        handle.write("transcript_id\tgene_id\n")
        for transcript, gene in sorted(transcript_to_gene.items()):
            handle.write(f"{transcript}\t{gene}\n")

    by_gene: dict[str, list[str]] = defaultdict(list)
    for transcript, gene in transcript_to_gene.items():
        by_gene[gene].append(transcript)
    with (outdir / "canonical_transcripts.tsv").open("w") as handle:
        handle.write("gene_id\tcanonical_transcript_id\tcds_bases\trule\n")
        for gene in sorted(by_gene):
            canonical = sorted(by_gene[gene], key=lambda tx: (-cds_bases.get(tx, 0), tx))[0]
            handle.write(
                f"{gene}\t{canonical}\t{cds_bases.get(canonical, 0)}\t"
                "longest_CDS_then_lexicographic_transcript_ID\n"
            )


def validate_cds_proteins(
    cds_path: Path,
    protein_path: Path,
    transcript_to_gene: dict[str, str],
) -> tuple[int, int, int]:
    cds_sequences = fasta_sequences(cds_path)
    protein_sequences = fasta_sequences(protein_path)
    cds_lengths = {key: len(value) for key, value in cds_sequences.items()}
    protein_lengths = {key: len(value) for key, value in protein_sequences.items()}
    expected = set(transcript_to_gene)
    if set(cds_lengths) != expected:
        raise ValueError("CDS FASTA transcript IDs do not exactly match GFF3 mRNA IDs")
    if set(protein_lengths) != expected:
        raise ValueError("Protein FASTA transcript IDs do not exactly match GFF3 mRNA IDs")

    inconsistent: list[str] = []
    incomplete_codon_records = 0
    for transcript in sorted(expected):
        cds = cds_lengths[transcript]
        protein = protein_lengths[transcript]
        if cds % 3:
            incomplete_codon_records += 1
        if cds // 3 - protein not in (0, 1):
            inconsistent.append(transcript)
            continue
        translated = translate_dna(cds_sequences[transcript]).rstrip("*")
        # This matched bundle uses a terminal period for the stop codon in
        # 58,622 protein records; normalize only that terminal convention.
        deposited = protein_sequences[transcript].rstrip("*.")
        if translated != deposited:
            inconsistent.append(transcript)
    if inconsistent:
        raise ValueError(
            "CDS/protein length concordance failed for: " + ", ".join(inconsistent[:10])
        )
    return len(cds_lengths), len(protein_lengths), incomplete_codon_records


def concatenate(paths: list[Path], destination: Path) -> None:
    with destination.open("wb") as writer:
        for path in paths:
            with path.open("rb") as reader:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host-fasta", default="data/reference/host/Lchinesis_genome.Chr.fasta.gz"
    )
    parser.add_argument(
        "--host-gff", default="data/reference/host/Lchinesis_genome.Chr.gff3.gz"
    )
    parser.add_argument(
        "--host-cds", default="data/reference/host/Lchinesis_genome.Chr.cds.gz"
    )
    parser.add_argument(
        "--host-protein", default="data/reference/host/Lchinesis_genome.Chr.pep.gz"
    )
    parser.add_argument(
        "--pathogen-fasta",
        default="data/reference/pathogen/GWHAOTU00000000.genome.fasta.gz",
    )
    parser.add_argument("--outdir", default="data/reference/combined")
    args = parser.parse_args()

    inputs = {
        name: ROOT / value
        for name, value in {
            "host_fasta": args.host_fasta,
            "host_gff": args.host_gff,
            "host_cds": args.host_cds,
            "host_protein": args.host_protein,
            "pathogen_fasta": args.pathogen_fasta,
        }.items()
    }
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    host_prefixed = outdir / "host.prefixed.fa"
    pathogen_prefixed = outdir / "pathogen.prefixed.fa"
    host_contigs = copy_prefixed_fasta(inputs["host_fasta"], host_prefixed, "HOST_")
    pathogen_contigs = copy_prefixed_fasta(
        inputs["pathogen_fasta"], pathogen_prefixed, "PATH_"
    )
    if set("HOST_" + item for item in host_contigs) & set(
        "PATH_" + item for item in pathogen_contigs
    ):
        raise ValueError("Host/pathogen prefixed contig collision")

    transcript_to_gene, transcript_counts, cds_bases, _, n_features = parse_gff(
        inputs["host_gff"], host_contigs
    )
    n_cds, n_proteins, n_incomplete_codon_records = validate_cds_proteins(
        inputs["host_cds"], inputs["host_protein"], transcript_to_gene
    )
    n_gtf_exons = write_annotations(
        inputs["host_gff"],
        outdir / "host.annotation.prefixed.gff3",
        outdir / "host.annotation.gtf",
        transcript_to_gene,
    )
    write_tx2gene_and_canonical(outdir, transcript_to_gene, cds_bases)

    combined = outdir / "host_pathogen.fa"
    concatenate([host_prefixed, pathogen_prefixed], combined)

    gffread = shutil.which("gffread")
    sibling_gffread = Path(sys.executable).resolve().parent / "gffread"
    if not gffread and sibling_gffread.is_file():
        gffread = str(sibling_gffread)
    if not gffread:
        raise RuntimeError("gffread is required to extract the transcriptome")
    subprocess.run(
        [
            gffread,
            str(outdir / "host.annotation.gtf"),
            "-g",
            str(host_prefixed),
            "-w",
            str(outdir / "host.transcripts.fa"),
        ],
        check=True,
    )
    transcriptome_lengths = fasta_lengths(outdir / "host.transcripts.fa")
    if set(transcriptome_lengths) != set(transcript_to_gene):
        raise ValueError("Extracted transcript IDs do not exactly match the GFF3 mRNA IDs")

    qc_rows = [
        ("host_contigs", len(host_contigs), "PASS"),
        ("host_bases", sum(host_contigs.values()), "PASS"),
        ("pathogen_contigs", len(pathogen_contigs), "PASS"),
        ("pathogen_bases", sum(pathogen_contigs.values()), "PASS"),
        ("gff_features", n_features, "PASS"),
        ("genes", len(transcript_counts), "PASS"),
        ("transcripts", len(transcript_to_gene), "PASS"),
        ("gtf_exons", n_gtf_exons, "PASS"),
        ("cds_records", n_cds, "PASS"),
        ("protein_records", n_proteins, "PASS"),
        ("CDS_records_with_terminal_incomplete_codon", n_incomplete_codon_records, "INFO"),
        ("extracted_transcripts", len(transcriptome_lengths), "PASS"),
        ("single_transcript_genes", sum(count == 1 for count in transcript_counts.values()), "INFO"),
        ("multi_transcript_genes", sum(count > 1 for count in transcript_counts.values()), "INFO"),
    ]
    with (outdir / "reference_qc.tsv").open("w") as handle:
        handle.write("metric\tvalue\tstatus\n")
        for metric, value, status in qc_rows:
            handle.write(f"{metric}\t{value}\t{status}\n")

    checksum_paths = [
        *inputs.values(),
        host_prefixed,
        pathogen_prefixed,
        combined,
        outdir / "host.annotation.prefixed.gff3",
        outdir / "host.annotation.gtf",
        outdir / "host.transcripts.fa",
        outdir / "transcript_to_gene.tsv",
        outdir / "canonical_transcripts.tsv",
        outdir / "reference_qc.tsv",
    ]
    with (outdir / "reference_checksums.sha256").open("w") as handle:
        for path in checksum_paths:
            handle.write(f"{sha256(path)}  {path.relative_to(ROOT)}\n")

    provenance = {
        "canonical_transcript_rule": "longest CDS; ties use lexicographically smallest transcript ID",
        "host_prefix": "HOST_",
        "pathogen_prefix": "PATH_",
        "inputs": {name: str(path.relative_to(ROOT)) for name, path in inputs.items()},
    }
    with (outdir / "reference_provenance.json").open("w") as handle:
        json.dump(provenance, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
