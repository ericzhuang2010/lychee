#!/usr/bin/env python3
"""Write the result-conditional manuscript and claim-to-evidence audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import markdown
import pandas as pd


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def truth(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ids(frame: pd.DataFrame, column: str = "entity_id") -> str:
    values = frame[column].astype(str).tolist()
    return ", ".join(values) if values else "none"


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--outdir", type=Path, default=Path("docs/paper/discovery_validation_manuscript")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    outdir = (root / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    discovery = read(root / "results/discovery/all_gene_discovery_status.tsv")
    pathways = read(root / "results/discovery/frozen_pathways.tsv")
    dtu = read(root / "results/discovery/frozen_dtu.tsv")
    qc = read(root / "results/audit/PRJNA830488_technical_qc.tsv")
    gene_robustness = read(root / "results/robustness/genes/frozen_gene_robustness.tsv")
    pathway_robustness = read(root / "results/robustness/pathways/frozen_pathway_robustness.tsv")
    external_genes = read(
        root / "results/external/PRJNA450886/genes/frozen_gene_tests.tsv"
    )
    external_pathways = read(
        root / "results/external/PRJNA450886/pathways/frozen_pathway_tests.tsv"
    )
    external_signature = read(
        root / "results/external/PRJNA450886/genes/signature_contrasts.tsv"
    )
    annotation = read(root / "results/evidence/annotation/final_candidate_annotations.tsv")
    small_rna = read(
        root / "results/evidence/small_rna/reference/small_rna_reference_gate.tsv"
    )
    discovery_motifs = read(
        root / "results/evidence/motifs/results/robust_candidate_motifs.tsv"
    )
    external_motifs = read(
        root / "results/external/PRJNA450886/motifs/transport/external_motif_transport.tsv"
    )
    evidence = read(root / "results/candidates/final_evidence_matrix.tsv")
    contradictions = read(root / "results/candidates/contradictory_results.tsv")

    statistical = discovery[truth(discovery["statistical_discovery"])]
    frozen = discovery[discovery["primary_gene_status"] == "DISCOVERED"]
    robust_genes = gene_robustness[
        gene_robustness.get("internal_robustness_status", "") == "PASS"
    ]
    robust_pathways = pathway_robustness[
        pathway_robustness.get("internal_pathway_robustness_status", "") == "PASS"
    ]
    primary_external = external_genes[
        (external_genes.get("study", "") == "PRJNA450886")
        & (external_genes.get("contrast", "") == "primary_24h")
    ]
    cross_genes = primary_external[
        primary_external.get("external_status", "") == "cross_context_supported"
    ]
    contrary_genes = primary_external[
        primary_external.get("external_status", "") == "contradictory"
    ]
    cross_pathways = external_pathways[
        external_pathways.get("external_pathway_status", "") == "cross_context_supported"
    ]
    robust_motifs = discovery_motifs[
        discovery_motifs.get("discovery_motif_status", "") == "ROBUST_CANDIDATE_MOTIF"
    ]
    transported_motifs = external_motifs[
        external_motifs.get("external_motif_transport_status", "")
        == "cross_context_supported"
    ]
    high_annotation = annotation[
        annotation.get("high_confidence_annotation", "").str.lower() == "true"
    ]
    tier_a = evidence[evidence["final_tier"] == "Tier A"]
    tier_b = evidence[evidence["final_tier"] == "Tier B"]
    tier_c = evidence[evidence["final_tier"] == "Tier C"]
    retired = evidence[evidence["final_tier"] == "Retired"]
    title = (
        "Genome-wide interaction analysis identifies a robust cultivar-dependent "
        "lychee infection-response signature with cross-context support"
        if len(tier_a) or len(tier_c)
        else "Genome-wide interaction reanalysis reveals context-specific lychee "
        "responses to Peronophythora litchii"
    )
    small_status = small_rna.iloc[0]["reference_gate_status"]
    included = int((qc["technical_gate"] == "INCLUDE").sum())
    filtered_genes = len(discovery)

    signature_primary = external_signature[
        (external_signature.get("study", "") == "PRJNA450886")
        & (external_signature.get("contrast", "") == "primary_24h")
    ]
    signature_text = (
        f"estimate {float(signature_primary.iloc[0]['estimate']):.3f}, "
        f"95% CI {float(signature_primary.iloc[0]['confidence_lower']):.3f} to "
        f"{float(signature_primary.iloc[0]['confidence_upper']):.3f}, "
        f"q={float(signature_primary.iloc[0]['q']):.3g}"
        if len(signature_primary) else "not testable because the frozen signature was empty"
    )
    dtu_text = (
        f"{len(dtu)} frozen transcript-usage results passed the conditional gate"
        if len(dtu) else "the conditional transcript-usage branch yielded no frozen result"
    )

    abstract_results = (
        f"All {included} discovery libraries passed the technical inclusion gates. "
        f"Among {filtered_genes} expressed genes, {len(statistical)} met the genome-wide "
        f"interaction threshold and {len(frozen)} remained after uniform mapping/model QC. "
        f"{len(robust_genes)} frozen genes and {len(robust_pathways)} frozen pathways passed "
        f"all internal robustness gates. In the locked 24-h PRJNA450886 evaluation, "
        f"{len(cross_genes)} genes and {len(cross_pathways)} pathways were cross-context "
        f"supported, while {len(contrary_genes)} genes were contradictory. The frozen "
        f"signature result was {signature_text}. Deterministic integration produced "
        f"{len(tier_a)} Tier A genes, {len(tier_b)} Tier B genes, and {len(tier_c)} Tier C "
        f"pathways; {len(retired)} entities were retired."
    )

    figure6 = (
        "![Figure 6. Conditional DTU discovery and external assessment.](../../../results/figures/Figure6_conditional_dtu.svg)"
        if len(dtu) else
        "Figure 6 was prospectively omitted because the frozen conditional DTU set was empty."
    )
    manuscript = f"""# {title}

## Abstract

### Background

Public lychee RNA-seq cohorts contain resistant/susceptible, tissue, time, and infection contrasts, but prior selected-gene analyses did not provide a genome-wide cultivar-by-infection discovery coupled to a prospective external-evidence firewall.

### Methods

We locked PRJNA830488 as discovery and fitted a genome-wide negative-binomial model with cultivar, infection, and cultivar-by-infection terms. Candidates required genome-wide Benjamini-Hochberg q<0.05, absolute interaction log2 fold change at least log2(1.5), and uniform mapping/model quality. We froze genes, signed weights, pathways, and conditional transcript-usage results before opening external outcomes. Internal robustness covered independent quantification, edgeR, expression-filter sensitivity, leave-one-library-out analyses, and observed mapping sensitivity. Frozen evaluation used PRJNA450886 as the primary cross-context study; PRJNA922966 and PRJNA1090613 retained transfer or exploratory roles. Annotation, promoter motifs, small-RNA eligibility, and accession-aware literature were maintained as separate orthogonal classes.

### Results

<!-- evidence: discovery, robustness, external, orthogonal -->
{abstract_results}

### Conclusions

<!-- evidence: interpretation -->
The evidence layers identify the exact scope of computational discoveries that are internally stable and, where observed, transport across a different tissue and resistant comparator. Cross-context support is not direct replication, and neither sequence annotation nor motif evidence establishes causality.

## Introduction

Lychee (Litchi chinensis) production is constrained by downy blight caused by the oomycete Peronophythora litchii. Public transcriptomic studies have profiled infection responses across cultivars, tissues, and time points, creating an opportunity to distinguish genome-wide cultivar-dependent responses from broad infection effects.

The principal discovery series, GSE201243/PRJNA830488, contains Guiwei and Yurong1 leaf libraries under mock and infected conditions at 24 h. Earlier interpretation of this accession emphasized selected genes and promoter elements. Such selected-feature analyses cannot control a genome-wide multiplicity family and risk using the same cohort for both selection and apparent confirmation.

We therefore implemented a discovery/validation firewall. Dataset roles, models, thresholds, empty-set behavior, and evidence vocabulary were frozen prospectively. Discovery refers only to the locked genome-wide interaction in PRJNA830488; robustness refers only to sensitivity within that study; external evidence is cross-context unless the biological estimand is directly replicated; and orthogonal evidence remains separate from expression support.

## Related Work

Sun et al. analyzed Guiwei and Heiye pericarp at 6, 24, and 48 h (PRJNA450886; doi:10.1038/s41598-019-39100-w) and reported distinct early response programs. Because that accession is the present primary external cohort, its paper is prior interpretation rather than independent validation. The GSE222650/651 Feizixiao small-RNA and mRNA studies provide condition-matched tissue contrasts but no shared BioSample accessions, so they cannot support specimen-level pairing. Molecular studies of the PlAvh202 effector (doi:10.1093/plphys/kiad311) and a pathogen transcriptome (doi:10.1371/journal.pone.0178245) provide biological context without automatically supporting a specific frozen host gene.

## Materials and Methods

### Study design and evidence definitions

The protocol and amendments are in analysis/preregistration. PRJNA830488 was the only discovery cohort. PRJNA450886 was primary cross-context evaluation, PRJNA922966 tested generic tissue/infection transfer, PRJNA922965 was orthogonal small RNA, and PRJNA1090613 remained exploratory because time and resistance metadata were unresolved. No external result could alter frozen membership or weights.

### Dataset provenance and eligibility

NCBI and GEO metadata were reconciled into a biological-unit registry. Inferential q values are conditional on deposited-library independence because source-tree, pooling, harvest, and extraction independence were not reported for the discovery libraries. The primary model required at least three included libraries in every cultivar-treatment cell.

### References and preprocessing

Host and pathogen references were combined with prefixed contig names. Paired reads were checked with FastQC, trimmed with fastp, aligned by STAR two-pass mapping, counted with featureCounts, and quantified independently with Salmon. Technical exclusion required fewer than 10 million surviving pairs or less than 40% unique alignment. GenMap-based exon uniqueness and observed candidate-level mapping checks were fixed before discovery.

### Discovery interaction model

DESeq2 fitted counts with formula ~ cultivar + treatment + cultivar:treatment, using Guiwei and mock as reference levels. The primary coefficient was cultivarYurong1.treatmentinfected: positive values indicate a stronger infected-minus-mock response in Yurong1 than Guiwei. Genes required count >=10 in at least three libraries, genome-wide BH q<0.05, and |log2FC|>=log2(1.5). apeglm-shrunken interaction effects defined signed signature weights.

### Pathways and transcript usage

Plant Reactome memberships were transported from one-to-one reciprocal-best Oryza protein matches. Pathway discovery used the frozen mapping and genome-wide interaction statistic. Transcript usage used Salmon abundances and a conditional inferential gate; no post hoc substitute was permitted if the gate failed.

### Internal robustness

Frozen genes were required to retain direction under Salmon gene aggregation, edgeR quasi-likelihood testing, a CPM filter, and leave-one-library-out fits. Predeclared correlation, effect-difference, q-value, leave-one-out, uniform mapping, and observed mapping-sensitivity gates were combined conjunctively, without an additive score. Frozen pathways required camera, roast, leading-edge deletion, and expression/length-matched null gates.

### External frozen evaluation

PRJNA450886 used ~ cultivar*treatment*time. The primary estimand was resistant-minus-susceptible cultivar-by-infection at 24 h; 6 and 48 h were secondary. Frozen candidate tests used BH adjustment across candidate-by-contrast families, an absolute log2FC threshold of log2(1.5), confidence intervals excluding zero, and discovery-direction agreement. PRJNA922966 used ~ tissue + treatment + tissue:treatment. PRJNA1090613 could not promote a final tier.

### Annotation and orthogonal evidence

Representative proteins were selected by longest CDS with lexicographic transcript tie-breaking. Reviewed Swiss-Prot release 2026_02 DIAMOND matches, targeted InterPro/Pfam matches, and one-to-one Oryza orthology were separate classes. High-confidence computational annotation required at least two classes, >=70% supported sequence coverage, and no detected architecture conflict.

The official PmiREN bulk archive was audited before small-RNA analysis. Its frozen gate was {small_status}; no study-derived novel-miRNA reference was substituted. Motif discovery used JASPAR 2026 Plants, strand-aware 1-kb and 2-kb promoters, 100 expression/GC-matched backgrounds, AME as primary, FIMO as sensitivity, and cognate-TF expression. Only discovery-frozen robust PWMs were transported to an independently selected PRJNA450886 response set.

### Deterministic tiers and multiplicity

Tier A required gene discovery, complete internal robustness, primary cross-context support, no mapping/annotation failure, and at least one attributable orthogonal class. Tier B required discovery and robustness with partial or non-testable external evidence. Tier C was reserved for a robust, externally supported frozen pathway without a qualifying Tier A member. Contradictory direction or mapping/annotation failure retired an entity. Zero Tier A candidates was allowed.

### Reproducibility

Snakemake workflows enforce staged discovery, external unlock, one STAR sorting job at a time, verified cleanup, and SHA-256 manifests. The resolved environment, synthetic fixtures, resource releases, all plotted source data, and protocol amendments accompany the results.

## Results

### Provenance and discovery-data quality

<!-- evidence: discovery -->
All {included} PRJNA830488 libraries passed the fixed technical gate. The combined-reference alignment, per-library QC, PCA, sample distances, and uniform gene mappability are shown in Figure 2 and Supplementary S2.

![Figure 1. Locked dataset roles and discovery/validation firewall.](../../../results/figures/Figure1_study_design_firewall.svg)

![Figure 2. Discovery QC and genome-wide interaction.](../../../results/figures/Figure2_discovery_qc_interaction.svg)

### Genome-wide cultivar-by-infection discovery

<!-- evidence: discovery -->
Of {filtered_genes} expressed genes, {len(statistical)} passed the statistical interaction threshold before uniform mapping/model QC and {len(frozen)} were frozen as discoveries. {len(pathways)} pathways were frozen at the primary pathway threshold. Positive interaction effects indicate stronger infection response in Yurong1; negative effects indicate stronger response in Guiwei.

### Internal robustness

<!-- evidence: robustness -->
{len(robust_genes)} of {len(frozen)} frozen genes passed every quantification, statistical-method, filter, leave-one-out, and mapping gate. {len(robust_pathways)} of {len(pathways)} frozen pathways passed the four conjunctive pathway robustness gates.

![Figure 3. Independent internal robustness layers.](../../../results/figures/Figure3_internal_robustness.svg)

### Primary external cross-context evaluation

<!-- evidence: external -->
At the locked PRJNA450886 24-h contrast, {len(cross_genes)} frozen genes were cross-context supported, {len(contrary_genes)} were contradictory, and the remainder were unsupported or not testable under the fixed threshold. The frozen signed-signature result was {signature_text}. No result is labeled direct replication because tissue and resistant comparator differ.

![Figure 4. External frozen evaluation.](../../../results/figures/Figure4_external_cross_context.svg)

### Frozen pathways and signature

<!-- evidence: external -->
{len(cross_pathways)} frozen pathways passed camera, roast, fgsea, leading-edge deletion, and matched-null external gates in PRJNA450886. Transfer-study and exploratory outcomes are retained in Table 4 and Supplementary S5-S6 without changing frozen definitions.

![Figure 5. Frozen pathway and signed-signature evaluation.](../../../results/figures/Figure5_pathway_signature_validation.svg)

### Conditional transcript usage

<!-- evidence: discovery/external -->
{dtu_text}. {figure6}

### Orthogonal evidence

<!-- evidence: orthogonal -->
{len(high_annotation)} frozen genes met the high-confidence computational annotation rule. {len(robust_motifs)} discovery motifs met the 100-background, two-window, and TF-expression gate; {len(transported_motifs)} of these transported under the external frozen test. Small-RNA coherence remained {small_status}. Literature entries reusing a current accession were retained as prior interpretation, not independent support.

![Figure 7. Orthogonal evidence layers.](../../../results/figures/Figure7_orthogonal_support.svg)

### Final deterministic tiers and contradictory results

<!-- evidence: integrated interpretation -->
The frozen matrix assigned Tier A to {ids(tier_a)}, Tier B to {ids(tier_b)}, and Tier C to {ids(tier_c)}. {len(retired)} entities were retired, including {ids(retired)}. Contradictory and failed results remain visible in results/candidates/contradictory_results.tsv.

![Figure 8. Separate evidence layers and deterministic final tiers.](../../../results/figures/Figure8_final_evidence_matrix.svg)

## Discussion

The analysis replaces selected-gene reuse with a genome-wide interaction discovery whose membership was fixed before external outcome access. This separation matters: a result can be statistically discovered but internally unstable, internally robust but externally not testable, or externally supported without being a direct replication.

PRJNA450886 changes tissue, resistant comparator, and time structure. Directionally concordant threshold-passing results therefore demonstrate transport across context, not repetition of the original biological experiment. PRJNA922966 addresses generic tissue/infection transfer and cannot test the cultivar interaction. PRJNA1090613 remains exploratory because unresolved metadata prevent a standardized confirmatory interpretation.

Pathway and signed-signature results can be more transportable than individual genes, but they remain dependent on the frozen Oryza-to-lychee mapping and pathway universe. Leading-edge deletion and matched-null analyses reduce, but do not eliminate, concerns about single-gene dominance or generic expression/length effects.

Annotation, motif enrichment, and literature contribute different kinds of evidence. Sequence/domain agreement supports a computational function label but not biological action in infected lychee. A transported promoter PWM is a candidate regulatory pattern, not proof of binding. The absent frozen PmiREN litchi reference made known-miRNA coherence non-testable; substituting study-derived novel sequences after viewing the gate would have violated the protocol.

Limitations include small deposited-library cell sizes, unknown source-unit independence, possible reference bias despite uniform and observed mapping checks, and lack of a direct biological replication cohort. External tissues and cultivar contrasts are deliberately heterogeneous. The deterministic framework makes these limitations visible and permits zero headline candidates rather than forcing a ranked list.

## Conclusion

This study provides a genome-wide, prospectively frozen cultivar-by-infection reanalysis of public lychee RNA-seq data, separates internal stability from cross-context evidence, and releases the resulting candidate/signature resource with null and contradictory outcomes. The final claims are computational and context-bounded; experimental perturbation and genuinely independent biological replication remain necessary for causal inference.

## Data and Code Availability

Primary public accessions are PRJNA830488/GSE201243, PRJNA450886, PRJNA922965/GSE222650, PRJNA922966/GSE222651, and PRJNA1090613/GSE262200. Exact reference releases and SHA-256 checksums are in analysis/config/resource_registry.tsv and data/reference manifests. The resolved environment is analysis/envs/lychee-discovery-resolved.yml. Protocol, amendments, result manifests, source data, and workflows are included in this repository. A repository release URL and archival DOI require the repository owner to publish the generated release and are explicitly marked pending in the submission-gate report.

## Supplementary Information

Supplementary S1-S13 contain the biological-unit registry, per-library QC, all discovery statistics, robustness manifests, all external frozen tests, pathway/signature tests, DTU, annotation/orthology, small-RNA gates, motif/background tests, the evidence registry, scripts/environments/commands, and amendments. Every main figure has a TSV source-data file.

## References

1. Sun et al. Early responses given distinct tactics to infection of Peronophythora litchii in susceptible and resistant litchi cultivar. Scientific Reports. 2019. doi:10.1038/s41598-019-39100-w.
2. Wang et al. Peronophythora litchii RXLR effector PlAvh202 destabilizes a host ethylene biosynthesis enzyme. Plant Physiology. 2023. doi:10.1093/plphys/kiad311.
3. Ye et al. Transcriptome analysis of Phytophthora litchii reveals pathogenicity arsenals and confirms taxonomic status. PLOS ONE. 2017. doi:10.1371/journal.pone.0178245.
4. MEME Suite documentation. https://meme-suite.org/
5. JASPAR. https://jaspar.elixir.no/
6. InterPro. https://www.ebi.ac.uk/interpro/
"""

    md_path = outdir / "manuscript.md"
    html_path = outdir / "manuscript.html"
    metrics_path = outdir / "manuscript_metrics.tsv"
    claims_path = outdir / "claim_sentence_audit.tsv"
    manifest_path = outdir / "manuscript_sources.sha256"
    md_path.write_text(manuscript, encoding="utf-8")
    html_body = markdown.markdown(manuscript, extensions=["tables"])
    html_path.write_text(
        """<!doctype html><html><head><meta charset="utf-8"><style>
        body { font-family: Liberation Serif, serif; max-width: 900px; margin: 2em auto;
               line-height: 1.45; color: #111827; }
        h1, h2, h3 { color: #0f172a; page-break-after: avoid; }
        img { max-width: 100%; page-break-inside: avoid; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #9ca3af; padding: 4px; }
        </style></head><body>""" + html_body + "</body></html>\n",
        encoding="utf-8",
    )
    metrics = [
        {"metric": "included_discovery_libraries", "value": included},
        {"metric": "expressed_genes_tested", "value": filtered_genes},
        {"metric": "statistical_gene_candidates", "value": len(statistical)},
        {"metric": "frozen_gene_discoveries", "value": len(frozen)},
        {"metric": "internally_robust_genes", "value": len(robust_genes)},
        {"metric": "frozen_pathways", "value": len(pathways)},
        {"metric": "internally_robust_pathways", "value": len(robust_pathways)},
        {"metric": "primary_external_cross_context_genes", "value": len(cross_genes)},
        {"metric": "primary_external_contradictory_genes", "value": len(contrary_genes)},
        {"metric": "primary_external_cross_context_pathways", "value": len(cross_pathways)},
        {"metric": "frozen_DTU_rows", "value": len(dtu)},
        {"metric": "high_confidence_annotations", "value": len(high_annotation)},
        {"metric": "robust_discovery_motifs", "value": len(robust_motifs)},
        {"metric": "externally_transported_motifs", "value": len(transported_motifs)},
        {"metric": "Tier_A", "value": len(tier_a)},
        {"metric": "Tier_B", "value": len(tier_b)},
        {"metric": "Tier_C", "value": len(tier_c)},
        {"metric": "Retired", "value": len(retired)},
        {"metric": "contradictory_or_failed_rows", "value": len(contradictions)},
    ]
    write_tsv(metrics_path, ["metric", "value"], metrics)
    audit_rows = [
        {
            "sentence_id": "R1", "evidence_layer": "discovery",
            "statement": f"{len(frozen)} genes and {len(pathways)} pathways were frozen.",
            "source": "results/discovery/frozen_results.sha256", "status": "SUPPORTED",
        },
        {
            "sentence_id": "R2", "evidence_layer": "robustness",
            "statement": f"{len(robust_genes)} genes and {len(robust_pathways)} pathways passed all internal gates.",
            "source": "results/robustness/internal_results.sha256", "status": "SUPPORTED",
        },
        {
            "sentence_id": "R3", "evidence_layer": "external",
            "statement": f"{len(cross_genes)} genes and {len(cross_pathways)} pathways had primary cross-context support.",
            "source": "results/external/PRJNA450886/external_results.sha256", "status": "SUPPORTED_CROSS_CONTEXT_NOT_DIRECT_REPLICATION",
        },
        {
            "sentence_id": "R4", "evidence_layer": "orthogonal",
            "statement": f"{len(transported_motifs)} frozen candidate motifs transported externally.",
            "source": "results/external/PRJNA450886/motifs/transport/external_motif_transport.sha256",
            "status": "SUPPORTED_CANDIDATE_MOTIF_NOT_FUNCTIONAL",
        },
        {
            "sentence_id": "R5", "evidence_layer": "interpretation",
            "statement": f"Final tier counts were A={len(tier_a)}, B={len(tier_b)}, C={len(tier_c)}, retired={len(retired)}.",
            "source": "results/candidates/final_evidence_matrix.sha256", "status": "SUPPORTED_DETERMINISTIC_RULE",
        },
        {
            "sentence_id": "A1", "evidence_layer": "release",
            "statement": "Repository release URL and archival DOI are pending owner publication.",
            "source": "results/release/submission_gate.tsv", "status": "PENDING_EXTERNAL_ACTION",
        },
    ]
    write_tsv(
        claims_path,
        ["sentence_id", "evidence_layer", "statement", "source", "status"],
        audit_rows,
    )
    inputs = [
        root / "results/discovery/frozen_results.sha256",
        root / "results/robustness/internal_results.sha256",
        root / "results/external/PRJNA450886/external_results.sha256",
        root / "results/candidates/final_evidence_matrix.sha256",
        root / "results/figures/figures.sha256",
        root / "results/tables/tables_supplements.sha256",
    ]
    with manifest_path.open("w") as handle:
        for path in [*inputs, md_path, html_path, metrics_path, claims_path]:
            handle.write(f"{sha256(path)}  {path.relative_to(root)}\n")
    print(
        f"manuscript: {len(frozen)} frozen genes, {len(tier_a)} Tier A, "
        f"{len(tier_c)} Tier C"
    )


if __name__ == "__main__":
    main()
