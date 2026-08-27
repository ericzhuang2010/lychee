# Revision plan: work remaining on the heavy-duty machine

This document tracks the response to `review_commnets_for_unified_manuscript.md`.
Part 1 records what was already addressed on the light machine (text edits plus
computations from frozen, checksummed tables only; no model was refit). Part 2
specifies, task by task, what must be done on the machine that holds the full
data (raw FASTQ, alignments, count matrices, and intermediate results excluded
from this repo by `.gitignore`).

The new numbers cited in the revised manuscript are reproduced by
`docs/paper/unified_manuscript/revision_analyses.py`, which reads only frozen
supplement/table artifacts (the genome-wide edgeR table was restored from git
history; its SHA-256 matches the frozen S4 manifest).

---

## Part 1. Addressed in this revision (light machine)

| Reviewer point | What was done |
|---|---|
| Title/terminology overclaim ("validation") | Title now says "genome-wide analysis with cross-context external evaluation"; "discovery/validation protocol" became "discovery and external-evaluation protocol"; keyword list updated; terminology swept throughout. |
| Candidate hierarchy (262 / 206 / 19 / 16) | Adopted explicitly in Abstract, Results 2.6, and Conclusions; the 206 are consistently called "statistical candidates". |
| edgeR gate opacity | Methods 5.7 now specifies TMM, robust estimateDisp/glmQLFit, glmQLFTest on the same interaction coefficient, genome-wide BH over all 19,445 genes, gate q < 0.10 plus direction agreement. Results 2.6 adds the concordance analysis: effects correlate at r = 0.995 (all genes) and 0.999 (206 candidates), 100% sign agreement, all 206 nominal edgeR P < 0.05; the 19-of-206 gap is significance calibration (edgeR admits only 24 genes genome-wide at q < 0.10), not effect disagreement. |
| QC-after-testing multiplicity concern | Recomputed BH over the 13,602 QC-eligible genes: all 206 frozen candidates rediscovered plus 12 more, so the registered ordering was conservative. Stated in Results 2.4 and Methods 5.5. |
| "Empirically independent" zero-overlap claim | Removed. Replaced with the hypergeometric facts (expected overlap 0.155; P(zero) = 0.85) in Results 2.7 and Discussion. |
| No continuous concordance analysis | Added: Pearson r = −0.05 (95% CI −0.19 to 0.10), Spearman −0.04, sign concordance 51.6% (95/184) at the primary contrast. |
| Legacy-audit estimand conflation | Results 2.5 and Discussion now distinguish the interaction audit from the original within-cultivar claims; headline reworded to "met the genome-wide interaction criterion"; the audit no longer claims to refute the original claims. |
| Motif causal attribution | Discussion now states the two motif analyses differed in foreground, motif set, scoring, and criteria, so background choice is consistent with but not isolated as the cause. |
| Biology "theme" overstatement | Explicitly labeled a qualitative annotation clustering, not an enrichment result. |
| Registration chronology / blinding | Methods 5.1 documents protocol v1.0.0 frozen 2026-08-18 (SHA-256 ef668486...), 20 outcome-blind amendments, 3 post-outcome technical amendments, prior exposure to the published external study, and that the unlock is a computational safeguard, not blinding. Also stated in the Introduction and Results 2.1. |
| Point-null vs composite-null | Methods 5.5 now states the registered rule tests beta = 0 with an effect filter, and that a composite-null test would be stricter (sensitivity analysis deferred; see H2). |
| Shrunken vs unshrunken estimates | Stated: unshrunken ML estimates everywhere; apeglm only for signature weights. Threshold decomposition added (277 q-only, 5,370 effect-only, 262 both). |
| External candidates table | New Table 3: the 2 supported and 5 contradictory genes with discovery/external effects, CIs, and q-values. |
| Tier B "Partial" opacity | Table 4 now shows numeric external effect, 95% CI, and q per gene; text notes all 9 measurable Tier B genes were direction-consistent. |
| Retirement category conflation | Results 2.11 separates mapping/annotation failures from directional contradictions and says why they differ in kind. |
| Tier A reachability | Results 2.11 notes Tier A was structurally hard to reach given the reference ecosystem, so the empty tier partly reflects that constraint. |
| Cultivar comparability (Yurong1 vs Heiye) | Results 2.7 reframes the external test as cross-cultivar response transport, not resistance validation. |
| External model time coding | Methods 5.8: time categorical, 24 h reference. |
| Robustness gate details | Methods 5.7: Salmon gate (direction + max 0.5 log2 difference), LOO gate (direction 12/12, q < 0.10 in ≥ 10/12), CPM-filter gate. |
| Power caveat | Discussion limitations now state unsupported outcomes conflate power, context dependence, and absence of effect (formal analysis deferred; see H3). |
| "Unsupported at prespecified thresholds" | Swept into Results 2.7, 2.9, 2.11. |
| Nomenclature | lychee/litchi standardized (crop "lychee"; "litchi downy blight" retained as disease name); *Phytophthora litchii* synonymy noted at first mention. |
| Declarations | Funding / conflicts / author-contributions section added (placeholder wording; confirm before submission). |
| Diagonal in Figure 3C | Caption now says the diagonal is a visual reference only. |

## Part 2. Heavy-machine tasks (full data, moderate-to-heavy compute)

### H1. Within-cultivar audit of the 18 legacy genes (highest priority)
The revised text promises this as follow-up. Fit infected-versus-mock contrasts
separately for Guiwei and Yurong1 under the confirmatory pipeline (same
featureCounts matrix, DESeq2 per-cultivar design `~ treatment`, BH within each
contrast genome-wide), extract the 18 legacy genes, and report log2FC, SE, and
q per cultivar. Deliverables: a supplementary table (proposed S14) plus two to
three sentences in Results 2.5 stating how many of the original within-cultivar
claims survive the confirmatory pipeline. Inputs: discovery count matrix
(`results/discovery/primary/`), adapt `analysis/scripts/08_primary_discovery.R`.
Compute: minutes.

### H2. Composite-null (lfcThreshold) sensitivity analysis
Rerun the primary DESeq2 results call with `lfcThreshold = log2(1.5)`
(composite null) genome-wide, plus apeglm s-values as a secondary view. Report
how many of the 262/206/19/16 survive. Deliverable: one Methods sentence and
one Results sentence, plus a supplement column in S3. Labeled post hoc
sensitivity, not a protocol change. Compute: minutes.

### H3. Simulation-based power analysis
Simulate counts from the fitted discovery model (per-gene means and dispersions,
3 libraries per cell) across a grid of interaction effect sizes; estimate power
at genome-wide q < 0.05 plus effect filter; repeat for the external design
(candidate-family adjustment). Deliverable: supplementary figure giving the
minimum detectable interaction log2FC at 80% power, and one Discussion sentence
replacing the current qualitative caveat. Compute: the heaviest item (hours);
parallelize over genes.

### H4. Replicate-level count plots for headline genes
Normalized counts per library (12 discovery libraries) for the 2 supported, the
12 Tier B, and the top legacy genes (LITCHI001510, LITCHI019519), as a
supplementary figure. Inputs: `normalized_counts.tsv`. Extend
`35_generate_figures_tables.py` so the figure regenerates with the asserted
source-data pattern. Compute: trivial; done there to keep figure provenance in
one pipeline.

### H5. Controlled motif-background comparison
The revised Discussion states this "remains to be done": rerun the
exploratory-stage motif counting for the same 18 promoters and the same
PlantCARE element set, changing only the background (randomized GC-matched
versus expression- and GC-matched genomic), to isolate the background effect.
Deliverable: small supplement table; upgrade the Discussion claim if the result
is clean. Inputs: promoter FASTA, background machinery from
`26_prepare_motif_inputs.py`/`28_motif_enrichment.py`. Compute: moderate.

### H6. PCA variance percentages (reviewer minor)
Recompute variance explained for PC1/PC2 from the VST counts and add
percentages to Figure 1C axis labels. Requires regenerating the figure source
data (the current frozen source data does not carry variance fractions), then
re-running `build_figures.py`. Compute: trivial.

### H7. Figure restructuring (editorial, optional)
Split Figure 5 (currently panels A–E) into a transcript-usage figure and an
orthogonal-evidence/tiers figure; consider moving the exploratory PRJNA1090613
signature panel of Figure 4B to the supplement. Regenerate via the frozen
figure pipeline so source-data assertions still pass.

### H8. Dataset search and eligibility documentation
Reconstruct how the five cohorts were found (GEO/SRA query terms, date, hits,
exclusions with reasons) and add a short Methods sentence plus a supplementary
listing. This is documentation recovery, not computation.

### H9. Exact tool versions
Extract version numbers (STAR, Salmon, fastp, featureCounts, DESeq2, edgeR,
DRIMSeq/DEXSeq/stageR, MEME suite, DIAMOND, GenMap, Snakemake, R/Bioconductor)
from `analysis/envs/lychee-discovery-resolved.yml` and session logs on the
heavy machine, and add them to Methods 5.4–5.9 or an S12 column.

### H10. Archived release with DOI (user action)
Mint a Zenodo (or equivalent) archive of the protocol, amendment log, workflow
code, and frozen tables, and replace the "will accompany the revised
submission" sentence in Data and code availability with the DOI.

### Decisions to confirm before resubmission (no compute)
- Declarations wording added on the light machine (no funding, no conflicts,
  single-author contribution) — confirm accuracy.
- Whether to adopt the reviewer's exact title suggestion (current title keeps
  the two-stage arc; reviewer's version leads with "Prospectively registered").
- Target journal strategy given the methods-forward framing.

### Suggested execution order on the heavy machine
H1 → H2 (same session, same matrix) → H6 + H4 (figure pipeline session) →
H9 + H8 (documentation) → H5 → H3 (long-running) → H7 (optional) → H10 (last,
after content freezes).
