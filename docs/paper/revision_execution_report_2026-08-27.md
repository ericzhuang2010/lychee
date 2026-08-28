# Heavy-machine revision execution report — 2026-08-27

The machine-executable portion of `revision_plan_heavy_machine.md` is complete.
All reviewer-response analyses use the frozen deposited-library design and are
reported as post hoc sensitivity or power analyses where applicable; none changes
the registered discovery membership.

## Results by task

- **H1 — within-cultivar legacy audit:** complete. At genome-wide BH *q* < 0.05,
  13/18 legacy genes were significant in Guiwei and 16/18 in Yurong1. The counts
  also exceeding |log2FC| ≥ log2(1.5) were 13/18 and 15/18, respectively.
- **H2 — composite-null sensitivity:** complete. DESeq2 composite-null passes in
  the 262/206/19/16 hierarchy were 8/7/7/7; apeglm false-sign-or-small passes were
  149/113/18/15.
- **H3 — simulation power:** complete. Twelve effect sizes × 100 simulations were
  run for each design. Overall interpolated 80% MDEs were 2.443 log2FC (5.44-fold)
  for genome-wide discovery and 2.114 log2FC (4.33-fold) for external evaluation.
  At 1.5 log2FC, overall detection probabilities were 62.7% and 74.0%. The lowest
  expression quartile did not reach 80% power by 4 log2FC in either design. The
  external simulation used 177 fit-eligible frozen genes; the manuscript explicitly
  distinguishes this from the 184 genes measurable in the observed external table.
- **H4 — replicate-level plots:** complete. Figure S1 contains all 12 deposited
  discovery libraries for 16 genes (192 source-data rows).
- **H5 — controlled motif background:** complete. Four of seven element classes
  passed against expression/GC-matched genomic backgrounds, but ARE lost and ABRE
  gained significance relative to randomized-GC backgrounds. The missing original
  observed-motif TSV and foreground recount discrepancies remain explicit provenance
  limitations.
- **H6 — PCA variance:** complete. PC1 and PC2 explain 54.2% and 16.1% of variance.
- **H7 — figure restructuring:** complete. Transcript usage is Figure 5,
  orthogonal evidence/final tiers is Figure 6, and quarantined PRJNA1090613 signature
  evidence is Figure S3.
- **H8 — search/eligibility reconstruction:** complete. The 2026-08-27 retrospective
  NCBI search record and all inclusion/exclusion decisions are Supplementary S16a–b.
- **H9 — tool versions:** complete. Nineteen exact version/evidence rows are in S17.
- **H10 — DOI release preparation:** machine portion complete. The curated
  archive, manifest, and checksum sidecar are under `results/release/`. Zenodo sign-in,
  reserved DOI insertion, metadata approval, and publication remain author actions.

## Integrated manuscript

- Authoritative source: `docs/paper/unified_manuscript/manuscript.md`
- viXra-format DOCX: `docs/paper/lychee_plants_revised_vixra_format_integrated.docx`
- Matching 34-page PDF: `docs/paper/lychee_plants_revised_vixra_format_integrated.pdf`
- The original viXra template remains unchanged at
  `docs/paper/lychee_plants_revised_vixra_format.docx`.

The DOCX ZIP integrity test passed and contains nine embedded figures (six main and
three supplementary). The end-to-end revision validator returned `PASS`.

## Git and archive size policy

`results/supplement/S10_motif_background_tests.tsv` is retained locally but removed
from the current Git index and explicitly ignored because it is 104,079,013 bytes.
The final compressed DOI bundle is below 100,000,000 bytes, and no file exposed in
the current Git index reaches that threshold. The S10 blob remains in older Git
history; purging history would require a separate, destructive history rewrite and
coordinated force-push, so it was not performed automatically.

