# Supplementary material

Associated manuscript:

> Cultivar-dependent transcriptional responses of lychee (*Litchi chinensis*)
> to *Peronophythora litchii*: from exploratory candidate discovery to a
> prospectively registered genome-wide analysis with cross-context external
> evaluation

Author: Eric Zhuang  
Package date: 2026-09-01

This package is the supplement-only companion to `manuscript.pdf`. The associated
PDF is not duplicated in the ZIP. The exact PDF used to assemble this package has:

- size: 560,408 bytes
- SHA-256: `07dd844c8f7c2626717960009190190f7766a638f1105e3c1773efc4c3f05b42`

## Contents

- `supplementary_tables/`: Supplementary Tables S1--S18 as UTF-8,
  tab-delimited files with header rows. S16 is divided into S16a and S16b, so
  this directory contains 19 files.
- `supplementary_figures/`: Figures S1--S3 in vector PDF and 300-dpi PNG formats.
- `figure_source_data/`: tab-delimited source data and supporting frozen tables
  for the six main analytical figures and Figures S1--S3.
- `MANIFEST.tsv`: byte size and SHA-256 digest for every packaged file other than
  the manifest itself.

## Figure-source mapping

- Main Figure 1: `S1_biological_unit_registry.tsv`,
  `Figure2_discovery_qc_interaction_source_data.tsv`, and
  `UnifiedFigure1_PCA_source_data.tsv`.
- Main Figure 2: `S3_all_discovery_statistics.tsv`, `legacy_18_audit.tsv`,
  `Table3_internal_robustness.tsv`, and `Table4_external_evaluation.tsv`.
- Main Figure 3: `Table3_internal_robustness.tsv` and
  `Table4_external_evaluation.tsv`.
- Main Figure 4 and Figure S3:
  `Figure5_pathway_signature_validation_source_data.tsv`, with pathway
  robustness results in `Table3_internal_robustness.tsv`. Figure S3 is the
  `C_signatures` row for study `PRJNA1090613`.
- Main Figure 5: `Figure6_conditional_dtu_source_data.tsv`.
- Main Figure 6: `S8_annotation_orthology.tsv`,
  `Figure7_orthogonal_support_source_data.tsv`, and `tier_summary.tsv`.
- Figure S1: `FigureS1_replicate_level_counts_source_data.tsv`.
- Figure S2: `FigureS2_power_analysis_source_data.tsv` and
  `S18_power_simulation_mde.tsv`.

Files named above as S1, S3, S8, or S18 are in `supplementary_tables/`; the other
source files are in `figure_source_data/`.

## Scope and provenance

Raw sequencing reads, read alignments, downloaded software environments, caches,
and workflow intermediates are not redistributed. The analyzed public accessions
are PRJNA830488/GSE201243, PRJNA450886, PRJNA922966/GSE222651,
PRJNA922965/GSE222650, and PRJNA1090613/GSE262200.

Supplementary Table S10 is 104,079,013 bytes uncompressed and is intentionally
excluded from the Git working tree. The copy in this ZIP was recovered from the
previously generated DOI release archive and checked against its recorded
SHA-256 digest (`af5be52d940ef1a64be37dcc9f9c5e12782d02eababe819828283176d0d7479d`).

To verify the package after extraction, recompute SHA-256 for each file and
compare it with `MANIFEST.tsv`. License selection and the permanent DOI remain
author decisions to complete in the Zenodo record.
