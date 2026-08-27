#!/usr/bin/env python3
"""Synthetic closure test for annotation and all deterministic tier branches."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lychee_final_evidence_test_") as temporary:
        temp = Path(temporary)
        config = temp / "config.json"
        config.write_text(json.dumps({
            "annotation": {
                "minimum_query_coverage": 0.70,
                "high_confidence_minimum_classes": 2,
            },
            "tiers": {"allow_zero_tier_a": True},
        }))
        sequence = temp / "sequence.tsv"
        sequence_fields = [
            "gene_id", "canonical_transcript_id", "protein_length", "protein_md5",
            "swissprot_accession", "swissprot_description", "swissprot_query_coverage",
            "rice_ortholog_accession", "rice_query_coverage",
        ]
        write_tsv(sequence, sequence_fields, [
            {"gene_id": "g1", "canonical_transcript_id": "t1", "protein_length": 100,
             "protein_md5": "a", "swissprot_accession": "S1",
             "swissprot_description": "kinase", "swissprot_query_coverage": 0.9,
             "rice_ortholog_accession": "R1", "rice_query_coverage": 0.8},
            {"gene_id": "g2", "canonical_transcript_id": "t2", "protein_length": 100,
             "protein_md5": "b", "swissprot_accession": "S2",
             "swissprot_description": "transporter", "swissprot_query_coverage": 0.8,
             "rice_ortholog_accession": "", "rice_query_coverage": ""},
            {"gene_id": "g3", "canonical_transcript_id": "t3", "protein_length": 100,
             "protein_md5": "c", "swissprot_accession": "S3",
             "swissprot_description": "enzyme", "swissprot_query_coverage": 0.9,
             "rice_ortholog_accession": "R3", "rice_query_coverage": 0.9},
        ])
        interpro = temp / "interpro.tsv"
        interpro_fields = [
            "gene_id", "canonical_transcript_id", "protein_md5", "protein_length",
            "found", "match_count", "pfam_accessions", "interpro_accessions",
            "architecture_union_coverage", "interpro_status",
        ]
        write_tsv(interpro, interpro_fields, [
            {"gene_id": "g1", "canonical_transcript_id": "t1", "protein_md5": "a",
             "protein_length": 100, "found": True, "match_count": 2,
             "pfam_accessions": "PF1", "interpro_accessions": "IPR1",
             "architecture_union_coverage": 0.8, "interpro_status": "PRECOMPUTED_MATCHES_FOUND"},
            {"gene_id": "g2", "canonical_transcript_id": "t2", "protein_md5": "b",
             "protein_length": 100, "found": True, "match_count": 1,
             "pfam_accessions": "PF2", "interpro_accessions": "IPR2",
             "architecture_union_coverage": 0.4, "interpro_status": "PRECOMPUTED_MATCHES_FOUND"},
            {"gene_id": "g3", "canonical_transcript_id": "t3", "protein_md5": "c",
             "protein_length": 100, "found": False, "match_count": 0,
             "pfam_accessions": "", "interpro_accessions": "",
             "architecture_union_coverage": 0, "interpro_status": "NO_PRECOMPUTED_MATCH_SUBMIT_INTERPROSCAN"},
        ])
        annotation_out = temp / "annotation"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/33_finalize_annotation.py"),
            "--sequence-evidence", str(sequence), "--interpro-summary", str(interpro),
            "--config", str(config), "--outdir", str(annotation_out),
        ], check=True)
        annotation_rows = {row["gene_id"]: row for row in read_tsv(
            annotation_out / "final_candidate_annotations.tsv"
        )}
        assert annotation_rows["g1"]["annotation_status"] == "HIGH_CONFIDENCE_COMPUTATIONAL_FUNCTION"
        assert annotation_rows["g2"]["annotation_status"] == "HIGH_CONFIDENCE_COMPUTATIONAL_FUNCTION"
        assert annotation_rows["g3"]["annotation_status"] == "FAMILY_LEVEL_FUNCTION"
        subprocess.run(["sha256sum", "-c", str(annotation_out / "final_annotation.sha256")], check=True)

        discovery = temp / "discovery.tsv"
        write_tsv(discovery, [
            "gene_id", "statistical_discovery", "primary_gene_status", "interaction_log2fc",
            "interaction_q", "uniform_gene_qc_status",
        ], [
            {"gene_id": gene, "statistical_discovery": True, "primary_gene_status": status,
             "interaction_log2fc": 1, "interaction_q": 0.01,
             "uniform_gene_qc_status": "FAIL" if gene == "gC" else "PASS"}
            for gene, status in [
                ("gA", "DISCOVERED"), ("gB", "DISCOVERED"),
                ("gC", "RETIRED_MAPPING_FAILURE"), ("gD", "DISCOVERED"),
                ("gE", "DISCOVERED"),
            ]
        ])
        robustness = temp / "robustness.tsv"
        write_tsv(robustness, [
            "gene_id", "internal_robustness_status", "observed_mapping_sensitivity_status",
        ], [
            {"gene_id": gene, "internal_robustness_status": status,
             "observed_mapping_sensitivity_status": "PASS"}
            for gene, status in [("gA", "PASS"), ("gB", "PASS"), ("gD", "PASS"), ("gE", "FAIL")]
        ])
        final_annotations = temp / "annotations.tsv"
        write_tsv(final_annotations, [
            "gene_id", "high_confidence_annotation", "annotation_status",
            "reported_function", "annotation_failure",
        ], [
            {"gene_id": gene, "high_confidence_annotation": gene == "gA",
             "annotation_status": "HIGH_CONFIDENCE_COMPUTATIONAL_FUNCTION" if gene == "gA" else "FAMILY_LEVEL_FUNCTION",
             "reported_function": "synthetic", "annotation_failure": False}
            for gene in ["gA", "gB", "gD", "gE"]
        ])
        external_genes = temp / "external_genes.tsv"
        write_tsv(external_genes, [
            "gene_id", "contrast", "external_status", "direction_agrees",
        ], [
            {"gene_id": "gA", "contrast": "primary_24h", "external_status": "cross_context_supported", "direction_agrees": True},
            {"gene_id": "gB", "contrast": "primary_24h", "external_status": "unsupported", "direction_agrees": True},
            {"gene_id": "gD", "contrast": "primary_24h", "external_status": "contradictory", "direction_agrees": False},
            {"gene_id": "gE", "contrast": "primary_24h", "external_status": "not_testable", "direction_agrees": False},
        ])
        pathways = temp / "pathways.tsv"
        write_tsv(pathways, ["pathway", "NES", "padj"], [
            {"pathway": "P1", "NES": 2, "padj": 0.01},
            {"pathway": "P2", "NES": 2, "padj": 0.01},
        ])
        members = temp / "members.tsv"
        write_tsv(members, ["pathway", "gene_id"], [
            {"pathway": "P1", "gene_id": "gB"}, {"pathway": "P2", "gene_id": "gA"},
        ])
        pathway_robustness = temp / "pathway_robustness.tsv"
        write_tsv(pathway_robustness, ["pathway", "internal_pathway_robustness_status"], [
            {"pathway": "P1", "internal_pathway_robustness_status": "PASS"},
            {"pathway": "P2", "internal_pathway_robustness_status": "PASS"},
        ])
        external_pathways = temp / "external_pathways.tsv"
        write_tsv(external_pathways, ["pathway", "external_pathway_status"], [
            {"pathway": "P1", "external_pathway_status": "cross_context_supported"},
            {"pathway": "P2", "external_pathway_status": "cross_context_supported"},
        ])
        small_rna = temp / "small_rna.tsv"
        write_tsv(small_rna, ["reference_gate_status"], [
            {"reference_gate_status": "NOT_TESTABLE_REFERENCE_ABSENT"},
        ])
        discovery_motifs = temp / "discovery_motifs.tsv"
        write_tsv(discovery_motifs, ["matrix_id", "discovery_motif_status"], [
            {"matrix_id": "M1", "discovery_motif_status": "ROBUST_CANDIDATE_MOTIF"},
        ])
        motif_sites = temp / "motif_sites.tsv"
        write_tsv(motif_sites, ["gene_id", "matrix_id", "window_bp", "site_present"], [
            {"gene_id": "gA", "matrix_id": "M1", "window_bp": 1000, "site_present": True},
            {"gene_id": "gA", "matrix_id": "M1", "window_bp": 2000, "site_present": True},
        ])
        external_motifs = temp / "external_motifs.tsv"
        write_tsv(external_motifs, ["matrix_id", "external_motif_transport_status"], [
            {"matrix_id": "M1", "external_motif_transport_status": "cross_context_supported"},
        ])
        published = temp / "published.tsv"
        write_tsv(published, ["DOI", "gene_or_pathway", "independent_of_current_datasets"], [
            {"DOI": "10.test/p1", "gene_or_pathway": "P1", "independent_of_current_datasets": "true"},
        ])
        evidence_out = temp / "candidates"
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/34_finalize_evidence.py"),
            "--all-gene-discovery", str(discovery), "--gene-robustness", str(robustness),
            "--frozen-pathways", str(pathways), "--pathway-members", str(members),
            "--pathway-robustness", str(pathway_robustness),
            "--external-genes", str(external_genes), "--external-pathways", str(external_pathways),
            "--annotations", str(final_annotations), "--small-rna-gate", str(small_rna),
            "--discovery-motifs", str(discovery_motifs),
            "--candidate-motif-sites", str(motif_sites), "--external-motifs", str(external_motifs),
            "--published-registry", str(published), "--config", str(config),
            "--outdir", str(evidence_out),
        ], check=True)
        tiers = {
            (row["entity_type"], row["entity_id"]): row["final_tier"]
            for row in read_tsv(evidence_out / "final_evidence_matrix.tsv")
        }
        assert tiers == {
            ("gene", "gA"): "Tier A", ("gene", "gB"): "Tier B",
            ("gene", "gC"): "Retired", ("gene", "gD"): "Retired",
            ("gene", "gE"): "Exploratory", ("pathway", "P1"): "Tier C",
            ("pathway", "P2"): "Exploratory",
        }, tiers
        subprocess.run([
            "sha256sum", "-c", str(evidence_out / "final_evidence_matrix.sha256")
        ], check=True)
    print("final annotation and evidence-tier synthetic test PASS")


if __name__ == "__main__":
    main()
