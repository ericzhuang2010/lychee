#!/usr/bin/env python3
"""Assign traceable evidence statuses and deterministic candidate tiers without scoring."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
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


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def index_unique(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate {key} values")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def external_gene_status(row: dict[str, str] | None) -> str:
    if row is None:
        return "not_testable"
    status = row.get("external_status", "not_testable")
    if status != "unsupported":
        return status
    return "partial" if as_bool(row.get("direction_agrees", "")) else "unsupported"


def published_support(
    entity: str, rows: list[dict[str, str]]
) -> tuple[str, str]:
    matches = []
    for row in rows:
        targets = {norm(value) for value in row["gene_or_pathway"].split(";")}
        if norm(entity) in targets and row["independent_of_current_datasets"].lower() == "true":
            matches.append(row["DOI"])
    return (
        ("INDEPENDENT_EXACT_SUPPORT", ";".join(sorted(set(matches))))
        if matches else ("NO_INDEPENDENT_EXACT_SUPPORT", "")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-gene-discovery", required=True, type=Path)
    parser.add_argument("--gene-robustness", required=True, type=Path)
    parser.add_argument("--frozen-pathways", required=True, type=Path)
    parser.add_argument("--pathway-members", required=True, type=Path)
    parser.add_argument("--pathway-robustness", required=True, type=Path)
    parser.add_argument("--external-genes", required=True, type=Path)
    parser.add_argument("--external-pathways", required=True, type=Path)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--small-rna-gate", required=True, type=Path)
    parser.add_argument("--discovery-motifs", required=True, type=Path)
    parser.add_argument("--candidate-motif-sites", required=True, type=Path)
    parser.add_argument("--external-motifs", required=True, type=Path)
    parser.add_argument("--published-registry", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    json.loads(args.config.read_text())["tiers"]
    discovery_rows = [
        row for row in read_tsv(args.all_gene_discovery)
        if as_bool(row.get("statistical_discovery", ""))
    ]
    robustness = index_unique(read_tsv(args.gene_robustness), "gene_id")
    annotations = index_unique(read_tsv(args.annotations), "gene_id")
    primary_external_rows = [
        row for row in read_tsv(args.external_genes)
        if row.get("contrast") == "primary_24h"
    ]
    external_genes = index_unique(primary_external_rows, "gene_id")
    pathways = index_unique(read_tsv(args.frozen_pathways), "pathway")
    pathway_robustness = index_unique(read_tsv(args.pathway_robustness), "pathway")
    external_pathways = index_unique(read_tsv(args.external_pathways), "pathway")
    published = read_tsv(args.published_registry)
    small_rna_gate_rows = read_tsv(args.small_rna_gate)
    if len(small_rna_gate_rows) != 1:
        raise ValueError("small-RNA reference gate must contain exactly one row")
    small_rna_status = small_rna_gate_rows[0]["reference_gate_status"]

    robust_motifs = {
        row["matrix_id"] for row in read_tsv(args.discovery_motifs)
        if row.get("discovery_motif_status") == "ROBUST_CANDIDATE_MOTIF"
    }
    transported_motifs = {
        row["matrix_id"] for row in read_tsv(args.external_motifs)
        if row.get("external_motif_transport_status") == "cross_context_supported"
    }
    eligible_motifs = robust_motifs & transported_motifs
    windows_by_gene_motif: dict[tuple[str, str], set[str]] = defaultdict(set)
    all_windows = set()
    for row in read_tsv(args.candidate_motif_sites):
        all_windows.add(row["window_bp"])
        if as_bool(row.get("site_present", "")):
            windows_by_gene_motif[(row["gene_id"], row["matrix_id"])].add(row["window_bp"])
    motif_support: dict[str, list[str]] = defaultdict(list)
    for (gene, motif), windows in windows_by_gene_motif.items():
        if motif in eligible_motifs and all_windows and windows == all_windows:
            motif_support[gene].append(motif)

    fields = [
        "entity_type", "entity_id", "discovery_status", "discovery_effect",
        "discovery_q", "internal_robustness_status", "external_status",
        "external_study", "external_contrast", "mapping_status",
        "annotation_status", "reported_function", "small_rna_status",
        "motif_status", "motif_ids", "published_evidence_status",
        "published_dois", "orthogonal_classes", "orthogonal_class_count",
        "contradiction_status", "final_tier", "claim_limit",
    ]
    gene_output: list[dict[str, object]] = []
    for row in sorted(discovery_rows, key=lambda item: item["gene_id"]):
        gene = row["gene_id"]
        discovery_status = row["primary_gene_status"]
        internal = robustness.get(gene, {})
        annotation = annotations.get(gene, {})
        external = external_genes.get(gene)
        external_status = external_gene_status(external)
        mapping_failure = discovery_status.startswith("RETIRED_") or str(
            internal.get("observed_mapping_sensitivity_status", "")
        ).startswith("FAIL")
        annotation_failure = as_bool(annotation.get("annotation_failure", ""))
        orthogonal = []
        if as_bool(annotation.get("high_confidence_annotation", "")):
            orthogonal.append("high-confidence annotation")
        if small_rna_status == "COHERENCE_PASS":
            orthogonal.append("condition-level miRNA-mRNA coherence")
        motifs = sorted(motif_support.get(gene, []))
        if motifs:
            orthogonal.append("robust motif with external transport")
        published_status, published_dois = published_support(gene, published)
        if published_status == "INDEPENDENT_EXACT_SUPPORT":
            orthogonal.append("independent published evidence")
        robust = internal.get("internal_robustness_status", "NOT_APPLICABLE")
        if mapping_failure or annotation_failure or external_status == "contradictory":
            tier = "Retired"
        elif (
            discovery_status == "DISCOVERED"
            and robust == "PASS"
            and external_status == "cross_context_supported"
            and orthogonal
        ):
            tier = "Tier A"
        elif (
            discovery_status == "DISCOVERED"
            and robust == "PASS"
            and external_status in {"partial", "not_testable"}
        ):
            tier = "Tier B"
        else:
            tier = "Exploratory"
        claim = {
            "Tier A": "headline computational candidate with cross-context support; not causal or directly replicated",
            "Tier B": "robust discovery with partial or non-testable external evidence",
            "Retired": "do not advance; retain as contradictory or failed candidate",
            "Exploratory": "discovery-layer result only; no validation claim",
        }[tier]
        gene_output.append({
            "entity_type": "gene", "entity_id": gene,
            "discovery_status": discovery_status,
            "discovery_effect": row.get("interaction_log2fc", ""),
            "discovery_q": row.get("interaction_q", ""),
            "internal_robustness_status": robust,
            "external_status": external_status,
            "external_study": "PRJNA450886",
            "external_contrast": "primary_24h",
            "mapping_status": row.get("uniform_gene_qc_status", row.get("mappability_status", "")),
            "annotation_status": annotation.get("annotation_status", "NOT_APPLICABLE"),
            "reported_function": annotation.get("reported_function", ""),
            "small_rna_status": small_rna_status,
            "motif_status": "SUPPORTED_BOTH_WINDOWS" if motifs else "NO_GENE_ATTRIBUTABLE_TRANSPORTED_MOTIF",
            "motif_ids": ";".join(motifs),
            "published_evidence_status": published_status,
            "published_dois": published_dois,
            "orthogonal_classes": ";".join(orthogonal),
            "orthogonal_class_count": len(orthogonal),
            "contradiction_status": (
                "CONTRADICTORY_EXTERNAL_DIRECTION"
                if external_status == "contradictory"
                else "MAPPING_OR_ANNOTATION_FAILURE"
                if mapping_failure or annotation_failure
                else "NONE"
            ),
            "final_tier": tier, "claim_limit": claim,
        })

    tier_a_genes = {
        row["entity_id"] for row in gene_output if row["final_tier"] == "Tier A"
    }
    pathway_members: dict[str, set[str]] = defaultdict(set)
    for row in read_tsv(args.pathway_members):
        pathway = row.get("pathway", "")
        gene = row.get("gene_id", "")
        if pathway and gene:
            pathway_members[pathway].add(gene)
    pathway_output: list[dict[str, object]] = []
    for pathway, row in sorted(pathways.items()):
        internal = pathway_robustness.get(pathway, {}).get(
            "internal_pathway_robustness_status", "NOT_TESTABLE"
        )
        external = external_pathways.get(pathway, {}).get(
            "external_pathway_status", "not_testable"
        )
        published_status, published_dois = published_support(pathway, published)
        orthogonal = (
            ["independent published evidence"]
            if published_status == "INDEPENDENT_EXACT_SUPPORT" else []
        )
        contains_tier_a = bool(pathway_members.get(pathway, set()) & tier_a_genes)
        tier = (
            "Tier C"
            if internal == "PASS" and external == "cross_context_supported" and not contains_tier_a
            else "Retired"
            if external == "contradictory"
            else "Exploratory"
        )
        pathway_output.append({
            "entity_type": "pathway", "entity_id": pathway,
            "discovery_status": "FROZEN_PATHWAY",
            "discovery_effect": row.get("NES", ""),
            "discovery_q": row.get("padj", ""),
            "internal_robustness_status": internal,
            "external_status": external,
            "external_study": "PRJNA450886",
            "external_contrast": "primary_24h",
            "mapping_status": "NOT_APPLICABLE",
            "annotation_status": "NOT_APPLICABLE",
            "reported_function": pathway,
            "small_rna_status": "NOT_APPLICABLE",
            "motif_status": "NOT_APPLICABLE",
            "motif_ids": "",
            "published_evidence_status": published_status,
            "published_dois": published_dois,
            "orthogonal_classes": ";".join(orthogonal),
            "orthogonal_class_count": len(orthogonal),
            "contradiction_status": (
                "CONTRADICTORY_EXTERNAL_DIRECTION" if external == "contradictory" else "NONE"
            ),
            "final_tier": tier,
            "claim_limit": (
                "cross-context-supported pathway/module without a qualifying Tier A gene"
                if tier == "Tier C"
                else "supported pathway accompanying a Tier A gene; not an independent Tier C fallback"
                if contains_tier_a and internal == "PASS" and external == "cross_context_supported"
                else "exploratory pathway; no validation claim"
                if tier == "Exploratory"
                else "do not advance contradictory pathway"
            ),
        })

    output_rows = gene_output + pathway_output
    args.outdir.mkdir(parents=True, exist_ok=True)
    matrix = args.outdir / "final_evidence_matrix.tsv"
    claims = args.outdir / "final_claims.md"
    contradictions = args.outdir / "contradictory_results.tsv"
    summary = args.outdir / "tier_summary.tsv"
    manifest = args.outdir / "final_evidence_matrix.sha256"
    write_tsv(matrix, fields, output_rows)
    contradictory_rows = [
        row for row in output_rows
        if row["contradiction_status"] != "NONE" or row["final_tier"] == "Retired"
    ]
    write_tsv(contradictions, fields, contradictory_rows)
    tiers = ["Tier A", "Tier B", "Tier C", "Exploratory", "Retired"]
    write_tsv(summary, ["tier", "count"], [
        {"tier": tier, "count": sum(row["final_tier"] == tier for row in output_rows)}
        for tier in tiers
    ])
    counts = {tier: sum(row["final_tier"] == tier for row in output_rows) for tier in tiers}
    title_mode = (
        "transfer-supported"
        if counts["Tier A"] or counts["Tier C"] else "context-specific"
    )
    claims.write_text("\n".join([
        "# Frozen final claims", "",
        f"- Title mode: {title_mode}.",
        f"- Tier A genes: {counts['Tier A']}.",
        f"- Tier B genes: {counts['Tier B']}.",
        f"- Tier C pathways: {counts['Tier C']}.",
        f"- Exploratory entities: {counts['Exploratory']}.",
        f"- Retired entities: {counts['Retired']}.",
        "- Cross-context support is not direct replication.",
        "- Orthogonal annotation, motif, small-RNA, and literature evidence is not causal or functional validation.",
        "- Zero headline candidates was permitted prospectively.", "",
    ]), encoding="utf-8")
    input_paths = [
        args.all_gene_discovery, args.gene_robustness, args.frozen_pathways,
        args.pathway_members, args.pathway_robustness, args.external_genes,
        args.external_pathways, args.annotations, args.small_rna_gate,
        args.discovery_motifs, args.candidate_motif_sites, args.external_motifs,
        args.published_registry, args.config,
    ]
    with manifest.open("w") as handle:
        for path in [*input_paths, matrix, claims, contradictions, summary]:
            handle.write(f"{sha256(path)}  {path}\n")
    print(
        "final evidence: "
        + ", ".join(f"{tier}={counts[tier]}" for tier in tiers)
    )


if __name__ == "__main__":
    main()
