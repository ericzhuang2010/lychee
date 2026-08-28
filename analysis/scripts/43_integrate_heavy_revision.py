#!/usr/bin/env python3
"""Integrate H1--H9 heavy-machine results into the unified manuscript source."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one old block, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, new: str, label: str) -> str:
    if new in text:
        return text
    start_index = text.find(start)
    if start_index < 0:
        raise ValueError(f"{label}: start marker absent")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise ValueError(f"{label}: end marker absent")
    return text[:start_index] + new + text[end_index:]


def fmt_mde(row: dict[str, str]) -> str:
    value = row.get("mde_80_log2fc", "")
    if value not in ("", "NA", "nan"):
        numeric = float(value)
        return f"{numeric:.2f} log2FC ({2**numeric:.1f}-fold)"
    return row["status"].replace(">", "greater than ") + " log2FC"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manuscript", type=Path, default=Path("docs/paper/unified_manuscript/manuscript.md"))
    args = parser.parse_args()
    root = args.root.resolve()
    manuscript = (root / args.manuscript).resolve() if not args.manuscript.is_absolute() else args.manuscript
    text = manuscript.read_text(encoding="utf-8")

    mde_rows = read_tsv(root / "results/supplement/S18_power_simulation_mde.tsv")
    source_rows = read_tsv(root / "results/figures/source_data/FigureS2_power_analysis_source_data.tsv")
    design_rows = read_tsv(root / "results/revision/H3_power/simulation_design.tsv")
    overall_mde = {row["design"]: row for row in mde_rows if row["expression_quartile"] == "Overall"}
    discovery_label = "Discovery: genome-wide BH"
    external_label = "External: candidate-family BH"
    if set(overall_mde) != {discovery_label, external_label}:
        raise ValueError("H3 overall MDE rows are incomplete")
    power_15 = {
        row["design"]: float(row["power"])
        for row in source_rows
        if row["expression_quartile"] == "Overall" and math.isclose(float(row["interaction_log2fc"]), 1.5)
    }
    if set(power_15) != {discovery_label, external_label}:
        raise ValueError("H3 1.5-log2FC power rows are incomplete")
    family_size = {row["design"]: int(row["tested_family_size"]) for row in design_rows}
    if family_size.get(discovery_label) != 19_445 or family_size.get(external_label) != 177:
        raise ValueError(f"Unexpected H3 simulated family sizes: {family_size}")
    external_family_size = family_size[external_label]
    discovery_mde = fmt_mde(overall_mde[discovery_label])
    external_mde = fmt_mde(overall_mde[external_label])

    text = replace_once(
        text,
        "Principal-component analysis of the transformed counts separated libraries by cultivar on the first component and by infection status on the second, with no library isolated from its replicate group (Figure 1C).",
        "Principal-component analysis of the transformed counts separated libraries by cultivar on the first component (54.2% of variance) and by infection status on the second (16.1%), with no library isolated from its replicate group (Figure 1C).",
        "H6 PCA percentages",
    )

    text = replace_once(
        text,
        "Positive interaction effects (stronger infection response in Yurong1) and negative effects (stronger response in Guiwei) were both well represented.",
        "A post hoc composite-null sensitivity analysis asked the stricter question whether |β| exceeded log2(1.5), rather than testing β = 0 and filtering the estimate afterward. Eight of the 262 statistical candidates passed the DESeq2 composite-null test at *q* < 0.05; the corresponding counts were 7 of 206 QC-retained candidates, 7 of 19 edgeR-gated candidates, and 7 of 16 fully robust candidates. An apeglm false-sign-or-small analysis was less severe, with *s* < 0.05 for 149, 113, 18, and 15 genes in those four nested sets, respectively. These are post hoc sensitivity results, not a redefinition of the registered discovery set. Positive interaction effects (stronger infection response in Yurong1) and negative effects (stronger response in Guiwei) were both well represented.",
        "H2 result",
    )

    legacy_paragraph = (
        "Because the exploratory candidates were selected before any interaction *P*-values existed, the registered protocol included a formal audit of all 18 against the genome-wide analysis (Figure 2B; Table 2). None met the genome-wide interaction threshold. We then performed the estimand-aligned follow-up requested in review: separate confirmatory DESeq2 infected-versus-mock fits within each cultivar, with Benjamini–Hochberg adjustment over the same 19,445-gene universe in each contrast (Supplementary S14). Thirteen of the 18 legacy genes were significant in Guiwei and 16 of 18 in Yurong1 at *q* < 0.05; all 13 Guiwei genes and 15 of the 16 Yurong1 genes also exceeded |log2FC| ≥ log2(1.5). Thus most of the original within-cultivar response claims survive the confirmatory pipeline even though none supports a genome-wide cultivar-by-infection interaction. The strongest interaction-audit candidate, LITCHI001510, reached *q* = 0.080; the EF-hand calcium-binding gene LITCHI019519, whose selected-gene contrast of −3.4 had appeared most dramatic in the exploratory stage, reached only *q* = 0.106 despite a re-estimated interaction effect of −3.33; and the median genome-wide interaction *q* across the 18 candidates was 0.47. Two candidates, the osmotin/thaumatin-like gene LITCHI009301 and LITCHI028401, additionally failed uniform exon-mappability control, meaning their interaction estimates cannot be attributed unambiguously to a single locus. The audit therefore does not show that these genes are biologically inert. It shows that within-cultivar responsiveness and cultivar-dependent response are distinct claims, and only the latter fails here."
    )
    text = replace_between(
        text,
        "Because the exploratory candidates were selected before any interaction *P*-values existed",
        "\n\n**Table 2.",
        legacy_paragraph,
        "H1 legacy paragraph",
    )

    text = replace_once(
        text,
        "The exploratory cohort's estimate is reported for completeness and is not confirmatory.",
        "The exploratory cohort's estimate is reported separately in Figure S3 for completeness and is not confirmatory.",
        "H7 exploratory signature sentence",
    )
    text = replace_once(
        text,
        "![Figure 4. Frozen pathway and signature evaluation. (A) Discovery normalized enrichment scores for the six frozen pathways; only circadian rhythm passed all internal gates, and none was supported in the primary external evaluation. (B) The frozen signed 206-gene signature across the seven locked external and exploratory contrasts; filled points denote q < 0.05.](figures/figure4_pathways_signatures.png)",
        "![Figure 4. Frozen pathway and signature evaluation. (A) Discovery normalized enrichment scores for the six frozen pathways; only circadian rhythm passed all internal gates, and none was supported in the primary external evaluation. (B) The frozen signed 206-gene signature across the six non-exploratory external contrasts; filled points denote q < 0.05. The quarantined PRJNA1090613 estimate is in Figure S3.](figures/figure4_pathways_signatures.png)",
        "H7 Figure 4 caption",
    )

    text = replace_once(
        text,
        "Differential transcript usage was analyzed under a conditional gate registered in advance: stage-wise testing had to yield interpretable gene- and transcript-level error control, and no post hoc substitute was permitted if the gate failed. The gate passed, and 225 transcript-usage events across 152 genes were frozen from 15,790 tested transcripts (Figure 5A). External follow-up preserved the role separation of the cohorts (Figure 5C): in the primary cross-context study, 125 events were measurable but unsupported at the prespecified thresholds and 100 were not testable; in the generic-transfer study, annotation incompatibilities left all 225 untestable; and in the exploratory cohort, 4 events were supported and 5 contradictory; we report these outcomes descriptively and do not count them as primary external support, because that cohort's metadata could not be standardized. Transcript-level rewiring between cultivars therefore remains an internally supported, externally unconfirmed layer of the resource.",
        "Differential transcript usage was analyzed under a conditional gate registered in advance: stage-wise testing had to yield interpretable gene- and transcript-level error control, and no post hoc substitute was permitted if the gate failed. The gate passed, and 225 transcript-usage events across 152 genes were frozen from 15,790 tested transcripts (Figure 5A). External follow-up preserved the role separation of the cohorts (Figure 5B): in the primary cross-context study, 125 events were measurable but unsupported at the prespecified thresholds and 100 were not testable; in the generic-transfer study, annotation incompatibilities left all 225 untestable; and in the exploratory cohort, 4 events were supported and 5 contradictory; we report these outcomes descriptively and do not count them as primary external support, because that cohort's metadata could not be standardized. Transcript-level rewiring between cultivars therefore remains an internally supported, externally unconfirmed layer of the resource.",
        "H7 DTU paragraph",
    )
    text = replace_once(
        text,
        "![Figure 5. Transcript usage, orthogonal evidence, and final tiers. (A) Conditional differential-transcript-usage discovery. (B) Annotation status of the 206 QC-retained genes; no gene met the high-confidence two-class rule. (C) External DTU follow-up separated by locked study role. (D) Promoter-motif robustness against 100 expression- and GC-matched backgrounds and the small-RNA reference gate. (E) Deterministic final tiers over all 268 frozen entities.](figures/figure5_dtu_orthogonal.png)",
        "![Figure 5. Conditional transcript usage. (A) Discovery gate and event counts. (B) External follow-up of the 225 discovery events, separated by locked study role.](figures/figure5_transcript_usage.png)",
        "H7 Figure 5 split",
    )

    orthogonal_start = "The orthogonal evidence classes returned uniformly negative or non-testable results"
    orthogonal_end = "\n\n### 2.11"
    orthogonal_paragraph = (
        "The registered orthogonal evidence classes returned uniformly negative or non-testable results, and we report them as such rather than converting them into support. Computational annotation assigned family-level functional labels to 150 of the 206 candidates and left 56 unannotated, but no candidate met the registered high-confidence rule requiring two independent evidence classes with at least 70% supported coverage and no architecture conflict, largely because precomputed InterPro domain architectures were unavailable for all 206 proteins in this non-model species (Figure 6A). Registered promoter-motif discovery tested 927 JASPAR plant position-weight matrices in strand-aware 1-kb and 2-kb windows against 100 expression- and GC-matched genomic background sets. No motif passed in more than 4 of 100 backgrounds against a required 80, and none passed FIMO sensitivity (Figure 6B). Small-RNA coherence was not testable because the frozen PmiREN reference contained no exact *Litchi* entries.\n\nA separate post hoc controlled comparison held the published 18-promoter totals, six explicitly reported exact-element strings plus one standard PlantCARE TCA-element variant, scoring rule, and multiplicity correction fixed while changing only the background (Supplementary S15). The 100,000-set randomized-GC rerun closely reproduced the exploratory result. Against 100 expression- and GC-matched genomic promoter sets, ARE lost significance, ABRE gained it, and MeJA-responsive, TCA, and TC-rich classes remained significant: four of seven classes passed under either strategy, but the identity of one class changed. Background construction therefore affected the result but did not by itself explain the exploratory/registered discrepancy. This comparison is provenance-limited: the archived exploratory package omitted the observed-motif input TSV, and exact recounting from the current canonical 18 promoters reproduced the published total only for ARE. Accordingly, it cannot rescue a functional regulatory claim or establish which foreground representation generated the other published totals. Published studies reusing any analyzed accession, including the primary external study itself [5], remain registered as prior interpretation rather than independent support.\n\n![Figure 6. Orthogonal evidence and final tiers. (A) Annotation status of the 206 QC-retained genes. (B) Registered promoter-motif robustness and the small-RNA reference gate. (C) Deterministic final tiers over all 268 frozen entities.](figures/figure6_orthogonal_tiers.png)"
    )
    text = replace_between(text, orthogonal_start, orthogonal_end, orthogonal_paragraph, "H5/H7 orthogonal section")
    text = text.replace("(Figure 5E)", "(Figure 6C)", 1)

    text = replace_once(
        text,
        "The 12 Tier B genes are listed in Table 4. Nine were measurable in the primary external cohort, and all nine were direction-consistent with discovery, although none met the full support criteria.",
        "The 12 Tier B genes are listed in Table 4. Nine were measurable in the primary external cohort, and all nine were direction-consistent with discovery, although none met the full support criteria. Figure S1 exposes the normalized count of every individual discovery library for these 12 genes, the 2 cross-context-supported genes, and legacy highlights LITCHI001510 and LITCHI019519; every cultivar-treatment cell contains all three deposited replicates.",
        "H4 count-plot result",
    )

    power_section = f"""### 2.12 Parametric simulations quantify the interaction effects detectable with three libraries per cell

The post hoc power analysis simulated negative-binomial counts from the fitted gene-wise means and dispersions while preserving the four-cell discovery design and the 24-h four-cell external design (Figure S2; Supplementary S18). At each of 12 absolute interaction effects from 0 to 4 log2 units, 100 simulations were run sequentially. Genome-wide discovery used 19,445 tests with 262 injected targets per simulation, matching the observed statistical-candidate prevalence; the external analysis adjusted within the {external_family_size} frozen genes that passed the simulation's count and dispersion validity filters, with 2 injected targets matching the number of directionally supported genes. Seven additional genes were measurable in the observed 184-gene external contrast but were not fit-eligible for simulation, so the simulated multiplicity family is reported explicitly rather than equated with the observed family. The overall interpolated effect required for 80% detection was {discovery_mde} in discovery and {external_mde} in the external candidate-family analysis. At a true |interaction log2FC| of 1.5, overall detection probabilities were {power_15[discovery_label]:.1%} and {power_15[external_label]:.1%}, respectively. These values are conditional on fitted dispersions treated as known, deposited-library independence, and the simulated non-null prevalence; they quantify the low-power regime but cannot distinguish context dependence from absence of effect for any particular unsupported gene.

"""
    if "### 2.12 Parametric simulations" not in text:
        text = text.replace("\n## 3. Discussion\n", "\n" + power_section + "## 3. Discussion\n", 1)

    old_motif_discussion = (
        "The orthogonal layers contribute mainly disciplined null results, and we consider their inclusion one of the more useful aspects of the resource. The promoter-motif contrast between stages is consistent with background choice having produced the exploratory enrichment signal, but it does not isolate that cause: the two analyses differed simultaneously in foreground genes, motif definitions, scoring procedure, and robustness criteria, so the defensible statement is that the exploratory motif findings did not survive a more stringent and methodologically different analysis. A controlled comparison holding everything but the background construction fixed remains to be done. The annotation and small-RNA outcomes expose reference-ecosystem gaps (no precomputed InterPro architectures and no *Litchi* entries in the frozen miRNA reference) that bound what any computational study of this species can currently claim, and that will silently inflate confidence in studies that do not check them. Reporting these gaps as non-testable classes, rather than quietly substituting weaker evidence, is what keeps the final tiers interpretable."
    )
    new_motif_discussion = (
        "The orthogonal layers contribute mainly disciplined null results, and we consider their inclusion one of the more useful aspects of the resource. The post hoc controlled PlantCARE comparison now isolates the background rule as far as the archived inputs permit. It shows that genomic expression/GC matching changes which class passes—ARE is replaced by ABRE—but does not eliminate the MeJA, TCA, or TC-rich signals when the published foreground totals are held fixed. Background choice is therefore not a sufficient explanation for the failure of the registered JASPAR analysis; the changed foreground, motif representation, scoring, and robustness rule remain consequential. Because the original observed-motif TSV was not archived and most published totals cannot be reproduced from the current canonical promoters, the controlled result is a provenance audit rather than evidence of regulatory function. The annotation and small-RNA outcomes likewise expose reference-ecosystem gaps (no precomputed InterPro architectures and no *Litchi* entries in the frozen miRNA reference) that bound what any computational study of this species can currently claim."
    )
    text = replace_once(text, old_motif_discussion, new_motif_discussion, "H5 discussion")
    text = replace_once(
        text,
        "Unsupported external outcomes additionally conflate limited power, context dependence, and true absence of effect: with three libraries per design cell, minimum detectable interaction effects are large, and a simulation-based power analysis quantifying them has not yet been performed.",
        f"Unsupported external outcomes additionally conflate limited power, context dependence, and true absence of effect. The simulations quantify the first component: conditional 80% minimum detectable effects were {discovery_mde} for genome-wide discovery and {external_mde} for candidate-family external evaluation, with still poorer performance among low-expression genes. These conditional curves do not identify which unsupported genes are context-specific or truly null.",
        "H3 discussion limitation",
    )

    text = replace_once(
        text,
        "National Center for Biotechnology Information and Gene Expression Omnibus metadata for all five cohorts were reconciled into a biological-unit registry (Supplementary S1). Because source-tree, pooling, harvest, and extraction independence were not reported for the discovery libraries, all inferential *q*-values are conditional on deposited-library independence. The primary model required at least three included libraries in every cultivar-treatment cell.",
        "National Center for Biotechnology Information and Gene Expression Omnibus metadata for all five cohorts were reconciled into a biological-unit registry (Supplementary S1). The original repository preserved accession decisions but not the historical query log, so search coverage was reconstructed retrospectively on 27 August 2026 and is not represented as prospective provenance. A broad NCBI GEO series query returned six records and a corresponding BioProject query returned seven; a narrow SRA cross-check returned 42 experiment-level records. After collapsing the GSE222652 super-series, excluding PRJNA1157370 because it used *Colletotrichum gloeosporioides*, and excluding PRJNA268587/GSE63658 because it studied fruit senescence/storage without *P. litchii* inoculation, the five prespecified cohorts remained (Supplementary S16a–b). Because source-tree, pooling, harvest, and extraction independence were not reported for the discovery libraries, all inferential *q*-values are conditional on deposited-library independence. The primary model required at least three included libraries in every cultivar-treatment cell.",
        "H8 Methods",
    )

    text = replace_once(
        text,
        "The registered rule tests the point null of zero interaction and applies the effect threshold to the observed estimate; a composite-null test of |β| ≤ log2(1.5) would be more stringent and was not part of the registered protocol, which is one reason we label the output statistical candidates.",
        "The registered rule tests the point null of zero interaction and applies the effect threshold to the observed estimate. Post hoc sensitivity used DESeq2 with `lfcThreshold = log2(1.5)` and `altHypothesis = greaterAbs`, plus apeglm false-sign-or-small *s*-values for the same threshold; neither analysis modified frozen membership. To align the legacy audit with its original estimand, separate post hoc DESeq2 models (`~ treatment`) were fitted within Guiwei and Yurong1, using the same count matrix, 19,445-gene universe, and genome-wide Benjamini–Hochberg adjustment within each cultivar.",
        "H1/H2 Methods",
    )

    text = replace_once(
        text,
        "Published studies reusing any analyzed accession were registered as prior interpretation.",
        "Published studies reusing any analyzed accession were registered as prior interpretation. For the post hoc controlled PlantCARE comparison, published observed totals across the 18 legacy promoters were fixed and tested against (i) 100,000 simulated sets of eighteen 2-kb sequences at 34% GC and (ii) 100 genomic sets of eighteen promoters matched by mean-expression and promoter-GC quintiles with the same seeded minimum-distance rule used by the registered motif pipeline. The six reported motifs and one standard TCA variant, together with reverse complements, were counted and one-sided empirical *P*-values were adjusted across seven classes. The missing archived observed-motif TSV and canonical-promoter recount discrepancies were retained as explicit provenance limitations (Supplementary S15).",
        "H5 Methods",
    )

    simulation_methods = f"""### 5.10 Simulation-based power analysis

Negative-binomial parametric simulations used DESeq2 maximum-a-posteriori gene dispersions and fitted sample means from the discovery counts and from the 24-h subset of PRJNA450886. Fitted cultivar and treatment main effects and size factors were retained, background-gene interaction coefficients were set to zero, and equal numbers of positive and negative effects were injected at 12 absolute log2FC values (0, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 3.5, 4). Each value had 100 simulations. Discovery injected 262 targets and applied Benjamini–Hochberg correction over 19,445 genes plus the registered effect filter. External simulation injected 2 targets among the {external_family_size} frozen genes passing the simulation count and dispersion validity filters and additionally required the prespecified sign and a 95% interval excluding zero; the observed external table contained 184 measurable genes, seven of which were not fit-eligible for the simulation. Dispersions were treated as known during simulated Wald refits, making the curves conditional parametric power rather than a claim about population-level biological replication. Eighty-percent minimum detectable effects were linearly interpolated between grid points, with expression-quartile curves and Wilson intervals reported in Figure S2.

### 5.11 Tier rules, software versions, and reproducibility"""
    text = replace_once(text, "### 5.10 Tier rules and reproducibility", simulation_methods, "H3 Methods heading")

    text = replace_once(
        text,
        "All stages ran under Snakemake workflows [42] enforcing staged discovery, a controlled external unlock, verified cleanup, and SHA-256 manifests over inputs and outputs; the resolved software environment, synthetic test fixtures, per-figure source-data tables, and the amendment log are distributed with the repository. All five main figures are regenerated from frozen result tables by a single script that recomputes and asserts every headline count.",
        "All stages ran under Snakemake 9.25.2 workflows [42] enforcing staged discovery, a controlled external unlock, verified cleanup, and SHA-256 manifests over inputs and outputs. Confirmatory executables were FastQC 0.12.1, fastp 1.3.6, STAR 2.7.10b, featureCounts/Subread 2.1.1, Salmon 2.5.1, MEME Suite/AME/FIMO 5.5.9, and DIAMOND 2.2.5; GenMap 1.3.0 is recoverable from the pinned specification although its executable is absent from the reconstructed environment. Statistical work used R 4.3.3/Bioconductor 3.18 with DESeq2 1.42.0, apeglm 1.24.0, edgeR 4.0.16, DRIMSeq 1.30.0, DEXSeq 1.48.0, stageR 1.24.0, and BiocParallel 1.36.0 (Supplementary S17 records the evidence status of every version). The resolved environment, synthetic fixtures, per-figure source data, and amendment log are distributed with the repository. All six main figures are regenerated from frozen result tables by a script that recomputes and asserts every headline count.",
        "H9 versions and H7 figure count",
    )

    text = replace_once(
        text,
        "Supplementary tables S1–S13 provide the biological-unit registry, per-library quality control, all 19,445 discovery statistics, robustness manifests, all external frozen tests, pathway and signature tests, transcript-usage results, annotation and orthology evidence, the small-RNA gate record, all 752,724 motif-background tests, the accession-aware evidence registry, the script and environment inventory, and the protocol amendment log. Every main figure has a tab-separated source-data file.",
        "Supplementary tables S1–S18 provide the biological-unit registry, per-library quality control, all 19,445 discovery statistics (including composite-null and false-sign-or-small columns), robustness manifests, all external frozen tests, pathway/signature and transcript-usage results, annotation and orthology evidence, the small-RNA gate, all registered motif-background tests, the evidence registry, script/environment inventory, amendment log, within-cultivar legacy audit (S14), controlled PlantCARE background comparison (S15), reconstructed search queries and eligibility decisions (S16a–b), exact software versions (S17), and power minimum-detectable effects (S18). Figure S1 shows replicate-level normalized counts, Figure S2 the conditional power curves, and Figure S3 the quarantined exploratory signature estimate. Every main and supplementary analytical figure has tab-separated source data where applicable.\n\n![Figure S1. Replicate-level normalized counts for the two cross-context-supported genes, twelve Tier B genes, and two legacy highlights. Points are individual deposited libraries; bars show cultivar-treatment medians.](../../../results/figures/FigureS1_replicate_level_counts.png)\n\n![Figure S2. Parametric detection probability for cultivar-by-infection effects under genome-wide discovery and candidate-family external adjustment. Curves show the overall result and mean-expression quartiles; the dashed line marks 80% power.](../../../results/figures/FigureS2_power_analysis.png)\n\n![Figure S3. Quarantined PRJNA1090613 signed-signature estimate, retained as exploratory rather than confirmatory evidence.](figures/figureS3_exploratory_signature.png)",
        "supplement inventory",
    )

    manuscript.write_text(text, encoding="utf-8")
    print(f"integrated heavy revision into {manuscript}")
    print(f"discovery_mde={discovery_mde}")
    print(f"external_mde={external_mde}")


if __name__ == "__main__":
    main()
