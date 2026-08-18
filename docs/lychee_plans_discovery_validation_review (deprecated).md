# Review of the Lychee Manuscript Improvement and Execution Plans

## Review question

Do the two computational-only plans provide:

1. a genuinely new scientific discovery; and
2. credible validation through independent datasets, independent published evidence, orthogonal data types, or alternative computational methods?

Files reviewed:

- `docs/lychee_manuscript_improvement_plan.md`
- `docs/lychee_manuscript_execution_plan.md`

Review date: 18 July 2026.

---

## Executive verdict

The plans are strong on reproducibility, modern read processing, genome-wide statistics, and claim restraint. They are much better than the rejected manuscript.

However, they do **not yet guarantee a new discovery**, and they do **not yet enforce a valid discovery-versus-validation split**.

The main problems are:

1. the proposed novelty is still largely “a technically better reanalysis”;
2. external datasets are inspected before discovery candidates and validation criteria are frozen;
3. no currently usable public dataset directly reproduces the GSE201243 Guiwei–Yurong leaf interaction at 24 h;
4. alternative pipelines on the same reads measure robustness, not independent validation;
5. papers that analyze the same public datasets are prior interpretations, not additional validation cohorts;
6. quantitative validation pass/fail rules are missing;
7. candidate tiers are assigned only after all external evidence is examined, permitting circular favorable ranking.

The plans should be revised around the following architecture:

- **Discovery:** one locked analysis on one designated discovery dataset.
- **Internal robustness:** alternative tools and sensitivity analyses on that same dataset.
- **External evaluation:** untouched datasets analyzed only after discovery genes, pathways, directions, and thresholds are frozen.
- **Orthogonal support:** independent modalities or published evidence from non-overlapping biological material.
- **Claim calibration:** distinguish replication, cross-context support, robustness, and literature support.

With those changes, the paper could make a defensible new computational discovery and validate its transportability. Without them, the likely product remains a careful candidate-prioritization resource rather than a discovery paper.

---

## 1. What the current plans do well

### 1.1 They correctly replace selected-gene arithmetic

The improvement plan requires a genome-wide model:

```r
design = ~ cultivar + treatment + cultivar:treatment
```

This directly addresses the reviewers’ strongest statistical objection.

Strengths:

- all adequately expressed genes are tested;
- interaction uncertainty and BH q values are reported;
- the old 18 genes become an audit set;
- a null interaction result is allowed;
- leave-one-library-out and alternate-quantifier sensitivity are planned.

### 1.2 They distinguish causal claims from computational predictions

The improvement plan explicitly prohibits claims of:

- demonstrated mechanism;
- functional cis-elements;
- direct TF–target regulation;
- causal resistance genes.

This is appropriate for a computational-only study.

### 1.3 They include useful external data

The plans identify:

- GSE201243 / PRJNA830488;
- PRJNA450886;
- GSE222651 / PRJNA922966;
- GSE222650 / PRJNA922965;
- GSE262200 / PRJNA1090613.

They also recognize major context differences in cultivar, tissue, and time.

### 1.4 They improve annotation and pathway rigor

Useful improvements include:

- InterPro/Pfam/eggNOG/Swiss-Prot evidence;
- corrected LITCHI017676 and LITCHI019299 interpretation;
- ranked pathway analysis;
- expressed-gene backgrounds;
- orthology mapping and unmapped fractions;
- multiple-testing control.

### 1.5 They treat networks and motifs cautiously

The plans correctly:

- avoid WGCNA on only 12 samples;
- make PRJNA450886 network work exploratory;
- use matched real promoters;
- replace exact-string PlantCARE counts with PWMs;
- require motif FDR and sensitivity to promoter/background choices;
- prohibit functional motif claims.

### 1.6 They aim for full reproducibility

The execution plan includes:

- manifests/checksums;
- modern alignment/counting;
- alternate quantification;
- scripted figures;
- environments;
- clean reruns;
- complete all-gene result release.

These are necessary strengths, but they are quality controls—not by themselves new biological discovery.

---

## 2. Critical discovery gaps

## 2.1 “First full interaction analysis” may be novel analysis, not new biology

The improvement plan currently locates novelty in:

- FDR-controlled interaction testing;
- modern reprocessing;
- mapping-bias auditing;
- cross-study integration;
- annotation/pathway/motif improvements.

Those are valuable methodological contributions. They do not guarantee a new biological finding.

Possible outcomes include:

- no interaction genes pass FDR;
- the leading pathways reproduce known WRKY, ROS, lignin, or hormone themes;
- the top genes overlap existing GSE201243 gene-family papers;
- external data disagree because tissues and cultivars differ.

If that occurs, the paper is a reproducibility/resource paper, not a discovery paper.

### Required change

The plans should define a **specific discovery hypothesis** before analysis, for example:

> A frozen set of cultivar-dependent infection-response genes or pathways identified in Guiwei–Yurong leaves shows a consistent resistance-associated direction and temporal profile in an independent Guiwei–Heiye fruit time course.

This is testable and falsifiable. It is stronger than “rank candidates.”

## 2.2 The plans lack a discovery/validation firewall

In the execution plan:

- Stage 8.1 analyzes GSE262200 before the primary GSE201243 analysis;
- Stage 8 analyzes all external studies;
- Stage 9 integrates all results;
- Stage 10 assigns candidate tiers only afterward.

Thus, the same external results help define candidates and then appear to support them.

That is circular validation.

### Required change

Reorder the workflow:

1. test code on synthetic fixtures, not biological external outcomes;
2. freeze the discovery model, pathway collection, effect threshold, and candidate rule;
3. analyze GSE201243;
4. freeze genes, pathways, directions, and confidence thresholds by checksum;
5. only then open and analyze external studies;
6. label any changes after external analysis as exploratory.

If GSE262200 has already guided choices, it cannot be an untouched validation dataset.

## 2.3 There is no guaranteed direct replication dataset

The primary estimand is:

> infection effect in Yurong leaves at 24 h minus infection effect in Guiwei leaves at 24 h.

External studies differ:

- PRJNA450886: Heiye versus Guiwei fruit at 6/24/48 h;
- GSE222651: Feizixiao infection by tissue, no cultivar interaction;
- GSE262200: GW versus SFZ leaves, but time and SFZ phenotype are unresolved.

These datasets can test transportability and cross-context consistency, but currently not direct replication.

### Required terminology

- **Replicated:** same estimand in independent biological samples.
- **Cross-context supported:** same direction in a different genotype, tissue, or time.
- **Orthogonally supported:** supported by another modality or independent published evidence.
- **Robust:** survives alternative methods on the same data.

Do not use these terms interchangeably.

## 2.4 New-discovery analyses need to be elevated

The present plans emphasize DE, pathways, networks, and motifs. Much of that was already attempted in prior lychee work.

The plans should add one coherent secondary discovery layer. Recommended options:

### Option A — Conserved cultivar-response signature

Recommended core discovery.

1. Discover a signed gene/pathway interaction signature in GSE201243.
2. Freeze its members, weights, and expected directions.
3. Score the frozen signature in PRJNA450886 at 24 h.
4. Test 6 and 48 h only as secondary temporal transport.
5. Test the infection component in Feizixiao leaves/fruits.
6. Use GSE262200 as a final interaction holdout only if metadata are resolved and outcomes remain unopened.

Potential new contribution:

> A cross-cultivar, cross-tissue transcriptional signature that separates early resistance-associated response from susceptible response.

### Option B — Differential transcript usage

Higher novelty, moderate execution risk.

1. Quantify transcripts with Salmon.
2. Test cultivar×infection differential transcript usage using DRIMSeq, DEXSeq, or stageR.
3. Freeze significant genes/transcripts and isoform directions.
4. Test corresponding transcript usage in PRJNA450886 and GSE222651 where annotation/read support is adequate.
5. Require gene-model and mapping-quality checks.

Potential new contribution:

> Cultivar-dependent isoform switching not visible in gene-level DEG analysis.

### Option C — Host–pathogen read dynamics

Exploratory only unless depth is sufficient.

1. Use a combined host/pathogen reference.
2. quantify host, pathogen, and ambiguous fractions;
3. model pathogen-read fraction over time in PRJNA450886;
4. relate it to frozen host signatures;
5. compare patterns with published disease progression.

Potential contribution:

> Coordinated host transcriptional response and pathogen-RNA accumulation.

Limitations:

- the libraries were not designed as balanced dual RNA-seq;
- pathogen depth may be too low;
- read fraction is not a direct pathogen-burden measurement.

### Option D — miRNA–mRNA coherence

Orthogonal modality, not an independent cohort.

1. confirm GSE222650/651 biological pairing;
2. identify significant miRNAs and mRNAs;
3. require opposite treatment directions;
4. require target support from at least two prediction tools;
5. test enrichment of frozen discovery targets.

Potential contribution:

> A cross-modality regulatory-coherence hypothesis.

It must not be called target validation.

### Recommendation

Choose Option A as the central discovery. Add Option B only if transcript annotation and read quality pass a preflight gate. Treat Options C/D as secondary or supplementary, not additional headline stories.

---

## 3. Critical validation gaps

## 3.1 Alternative tools are robustness, not validation

The execution plan proposes:

- featureCounts versus Salmon;
- DESeq2 versus edgeR/limma;
- Wald versus LRT;
- alternate filters;
- leave-one-library-out;
- alternate promoter backgrounds.

These reuse the same biological samples.

They test:

- pipeline sensitivity;
- numerical stability;
- model dependence;
- mapping/quantification robustness.

They do not provide external biological validation.

### Required change

Create separate result columns:

- discovery significance;
- internal robustness;
- external support;
- orthogonal support.

Do not combine them into one vague validation score.

## 3.2 Biological-unit independence is a blocking issue

Three deposited libraries do not necessarily mean three independent trees or biological sources.

Unknown independence affects:

- dispersion estimates;
- P/q values;
- bootstrap design;
- external-validation claims.

### Required dataset eligibility gate

For each study, record:

- source tree/orchard;
- harvest;
- pooled material;
- extraction;
- BioSample;
- library;
- sequencing run;
- technical replicate relationship;
- treatment, tissue, time, and batch.

Eligibility for inferential validation should require:

1. at least three independent biological units per tested cell;
2. technical replicates collapsed;
3. full-rank model;
4. no perfect batch/treatment confounding;
5. no biological-source overlap with discovery data.

If independence remains unknown:

- use descriptive effects and uncertainty cautiously;
- label the study exploratory;
- do not call it independent replication.

## 3.3 GSE222650 and GSE222651 are one cohort

The long-RNA and small-RNA components share matching labels and arise from the same superseries.

They can provide:

- cross-modality coherence;
- orthogonal measurement;
- miRNA–mRNA directional consistency.

They count as one biological cohort, not two independent validations.

## 3.4 Publications can be support, but may not be independent evidence

A paper using the same accession is not another validation dataset.

Examples:

- the GSE201243 WRKY/CDPK papers are prior interpretations of the discovery dataset;
- the 2019 paper is the source publication for PRJNA450886;
- the 2023 ncRNA paper is the source publication for GSE222650/651.

Published evidence should be classified:

- **same-data prior interpretation;**
- **independent biological material;**
- **independent modality;**
- **functional evidence for the exact gene/pathway;**
- **general ortholog evidence only.**

Only independent biological material should count as independent validation.

## 3.5 Meta-analysis rules are underspecified

The plans say to meta-analyze “comparable effects,” but do not define comparability.

Different:

- cultivar pairs;
- tissues;
- times;
- protocols;
- references;
- source units

are not automatically exchangeable.

### Required change

Define an estimand registry before integration:

- exact contrast;
- tissue;
- time;
- genotype relationship;
- unit of analysis;
- direction convention.

Pool only when at least three independent studies test the same estimand. Otherwise present study-specific effects and heterogeneity without a pooled estimate.

---

## 4. Recommended computational validation framework

## Layer 0 — Dataset eligibility

Before outcome analysis:

1. complete the biological-unit registry;
2. classify each study as inferential, cross-context, descriptive, or ineligible;
3. freeze the role of each dataset;
4. prevent later role switching based on favorable outcomes.

Recommended roles:

- **GSE201243:** locked discovery dataset.
- **PRJNA450886:** locked temporal/cultivar cross-context evaluation; 24 h primary, 6/48 h secondary.
- **GSE222651:** generic infection/tissue transfer assessment; not cultivar-interaction validation.
- **GSE222650:** orthogonal modality within the GSE222652 cohort.
- **GSE262200:** untouched interaction holdout only after time, SFZ identity, phenotype, and biological units are resolved.
- **PRJNA1195217:** prospective future holdout only if public data and independence become available before analysis.

## Layer 1 — Locked discovery

Use only GSE201243.

Primary model:

```r
design = ~ cultivar + treatment + cultivar:treatment
```

Before running:

- freeze count filter;
- freeze factor references;
- freeze primary coefficient;
- freeze pathway collection;
- freeze candidate threshold;
- freeze fallback if no genes pass FDR.

Recommended gene-level discovery threshold:

- BH q<0.05;
- absolute interaction log2FC ≥ log2(1.5);
- adequate counts/mappability.

If no gene passes:

- report the null;
- use a prespecified pathway-level fallback;
- do not create a replacement top-gene list from raw P values.

After discovery:

- write genes, pathways, signs, weights, and expected external directions;
- checksum the frozen discovery file;
- open external outcomes only afterward.

## Layer 2 — Internal robustness

Compare:

- STAR–featureCounts versus Salmon–tximport;
- DESeq2 versus edgeR quasi-likelihood;
- primary count filter versus CPM>1 in ≥3 samples;
- all 12 leave-one-library-out fits;
- variant-aware or reference-swap sensitivity for leading loci.

Suggested prespecified pass criteria:

- genome-wide signed-statistic Spearman \(\rho\) ≥0.85;
- candidate sign agreement across pipelines;
- absolute LFC difference ≤0.5;
- q<0.10 in both DESeq2 and edgeR;
- same sign in 12/12 leave-one-out fits;
- q<0.10 in at least 10/12 leave-one-out fits;
- no unique-mappability or variant-aware failure.

These thresholds are recommendations and should be fixed before results. Passing means **robust**, not externally validated.

## Layer 3 — Locked external evaluation

For frozen genes/signatures, run preregistered directional tests only.

### PRJNA450886

Primary:

- 24-h Guiwei–Heiye cultivar×infection contrast;
- same direction expected as the frozen Guiwei–Yurong discovery signature.

Secondary:

- 6-h and 48-h temporal behavior.

Interpretation:

- cross-resistant-cultivar and cross-tissue support;
- not direct replication.

### GSE222651

Test:

- whether frozen infection-response genes/pathways change in the expected direction in Feizixiao leaves;
- whether effects generalize to fruit;
- tissue×infection heterogeneity.

Interpretation:

- generic infection and tissue transportability;
- cannot validate cultivar interaction.

### GSE262200

Use only if metadata are resolved before analysis.

It may become the best interaction holdout if:

- time is known and comparable;
- SFZ identity/resistance is documented;
- source units are independent;
- raw reads map to compatible identifiers.

If it has already been used for script tuning or biological decisions, label it development data rather than holdout validation.

### Suggested gene-level external pass criteria

Across the frozen candidate×contrast family:

- same preregistered direction;
- BH q<0.05;
- absolute LFC ≥ log2(1.5);
- 95% CI excludes zero;
- no mapping/annotation failure.

Use “replicated” only if the same estimand is tested. Otherwise use “cross-context supported.”

## Layer 4 — Pathway/signature validation

Recommended primary test:

- `limma::camera` for a fixed competitive gene-set test.

Sensitivity:

- `fgseaMultilevel`;
- `roast`.

A pathway/signature receives multi-study support only if:

1. the identical frozen gene set and direction are tested;
2. BH q<0.05 with the same direction in at least two independent studies;
3. removal of the largest leading-edge gene leaves q<0.10;
4. score exceeds 95% of matched random-gene-set nulls.

Do not redefine the gene set per external study.

## Layer 5 — Network and motif transport

### Network

If modules are discovered in PRJNA450886:

- use 500 source-unit-aware bootstraps;
- require membership Jaccard ≥0.70 in ≥80% of bootstraps;
- require eigengene interaction q<0.05;
- freeze membership;
- test the fixed module score in GSE201243 and GSE222651.

Formal preservation statistics in very small cohorts should be interpreted cautiously. Module-score consistency may be more credible.

### Motifs

Discover motifs only in the frozen discovery gene set.

Require:

- 100 matched backgrounds;
- BH q<0.05 in ≥80/100 backgrounds;
- odds ratio ≥1.5;
- agreement for 1-kb and 2-kb promoter windows;
- cognate TF family expression;
- frozen PWM enrichment in independently derived external gene sets.

Even if all criteria pass, call the result:

> cross-study-supported candidate TF-binding motif

Do not call it a binding site or functional cis-element.

## Layer 6 — Orthogonal evidence

### Annotation

High-confidence function should require at least two independent evidence classes:

- InterPro/Pfam domain architecture;
- reviewed Swiss-Prot homology;
- reciprocal orthology/OrthoFinder;
- catalytic-residue and full-length-model consistency.

Recommended minimum:

- ≥70% query/subject coverage;
- no conflicting domain architecture.

Otherwise retain family-level annotation.

### Small RNA

If pairing is confirmed:

- miRNA q<0.05;
- mRNA q<0.05;
- opposite treatment direction;
- target predicted by at least two tools such as psRNATarget and sPARTA.

Call this regulatory coherence, not target validation.

### Published evidence

Independent papers can strengthen plausibility when:

- biological material does not overlap;
- the exact gene/pathway is tested;
- evidence type is clearly recorded.

Do not award an independent-validation vote to the source paper for a reused dataset.

---

## 5. Review of the improvement plan

## 5.1 Strong sections

The following sections should be retained:

- **Scope and claim boundary**
- **1.3 genome-wide interaction correction**
- **1.4 expression QC**
- **1.5 removal of unmotivated analyses**
- **1.6 annotation correction**
- **3.2 modern processing/mapping bias**
- **3.3 primary interaction**
- **3.4 time-course analysis**
- **3.8 annotation/orthology**
- **3.9 ranked pathway analysis**
- **3.10 cautious network analysis**
- **3.11 in-silico promoter limitations**
- **3.13 reproducibility**

These create a strong technical foundation.

## 5.2 Sections requiring major revision

### Section 1.2 — Novelty

Problem:

- novelty is mostly methodological;
- there is no single falsifiable new biological discovery hypothesis;
- “first complete interaction analysis” may be incremental.

Add:

- one central cross-context signature hypothesis;
- one optional secondary discovery such as differential transcript usage;
- a novelty gate with documented literature search and fallback.

### Sections 2.2–2.5 — Dataset roles

Problem:

- dataset descriptions are good, but roles are not frozen;
- external studies can migrate between discovery and validation;
- GSE222650/651 may be double-counted.

Add:

- a dataset-role registry;
- eligibility rules;
- one biological-cohort vote for GSE222652;
- holdout quarantine for GSE262200.

### Section 3.6 — GSE262200 quick interaction

Problem:

- using biological results for quick code testing contaminates its potential holdout role.

Recommendation:

- test code on synthetic fixtures with known expected results;
- either reserve GSE262200 untouched or declare it development data.

### Section 3.7 — Cross-study integration

Problem:

- “comparable contrasts” is undefined;
- random-effects meta-analysis can be misapplied;
- external evidence enters candidate ranking before freezing.

Add:

- estimand registry;
- no pooling without ≥3 independent studies of the same estimand;
- discovery freeze before integration;
- study-specific effects when pooling is invalid.

### Section 3.10 — Network

Problem:

- “source-unit-aware bootstrap” cannot be implemented if source units remain unknown;
- “stable” lacks a threshold.

Add:

- provenance eligibility prerequisite;
- quantitative Jaccard/bootstrap/eigengene criteria;
- automatic removal from the main paper if failed.

### Section 3.11 — Promoters

Problem:

- no external motif-validation protocol;
- matched-background robustness is qualitative;
- no frozen motif transport test.

Add:

- 100-background rule;
- OR and window thresholds;
- frozen PWM external testing;
- TF-family expression requirement.

### Section 3.12 — Candidate tiers

Problem:

- tier definitions are qualitative;
- external evidence is already known when tiers are assigned;
- missing-evidence and conflict handling are undefined.

Replace with four independent statuses:

1. discovery;
2. internal robustness;
3. external support;
4. orthogonal support.

Then define a deterministic Boolean rule for any final headline candidate. Permit the highest tier to be empty.

### Sections 4–5 — Figures and manuscript

Problem:

- figures/network/motif outputs are listed even if stage gates fail;
- the proposed title still assumes cultivar-dependent prioritization.

Add conditional branches:

- null-interaction title and abstract;
- empty headline-candidate set;
- network/motif figures omitted or supplementary when unstable;
- reproducibility/resource framing when novelty fails.

---

## 6. Review of the execution plan

## 6.1 Discovery must precede external outcome analysis

Current sequence:

- Stage 4 downloads GSE262200 counts;
- Stage 8.1 analyzes GSE262200;
- Stage 8.2 then analyzes GSE201243;
- Stages 9–10 integrate and freeze candidates.

Required sequence:

1. preflight and synthetic tests;
2. freeze protocol/candidate rules;
3. GSE201243 discovery;
4. checksum discovery result;
5. locked external analysis;
6. orthogonal analyses;
7. candidate status assignment.

## 6.2 Add Stage 0 — Preflight

As of this review:

- the workspace `docs` directory contains the two plans, review feedback, and a skills-selection document;
- the manuscript PDF referenced by Stage 3 was not found at its stated workspace path;
- the S2/S3 ZIP files were not found at the referenced archive paths.

Therefore, current Stage 3 commands may fail.

Stage 0 should check:

- every required local path;
- URL reachability;
- expected file checksum/size;
- available disk and RAM;
- required executables;
- whether missing S2/S3 should be downloaded from Zenodo or reconstructed;
- whether the manuscript PDF/DOCX path changed.

Example behavior:

- missing optional asset → reconstruct/skip;
- missing primary input → block;
- insufficient disk → block before FASTQ download.

## 6.3 Reference strategy is not fully executable

Current issues:

- NCBI assembly is downloaded;
- Sapindaceae FASTA/GFF are used;
- compatibility is requested but lacks pass/fail criteria;
- Mendeley matched package is not operationalized;
- deposited GSE262200 counts may use a different annotation.

Add:

- one selected matched FASTA/GFF/CDS/protein bundle;
- contig-name/length equality;
- coordinate-bound checks;
- unique gene/transcript IDs;
- CDS/protein extraction concordance;
- canonical-transcript rules;
- ID-map coverage threshold for external count matrices.

If GSE262200 ID-map coverage is poor, reprocess raw reads or exclude it from gene-level validation.

## 6.4 Mapping-bias work is currently a promise, not a workflow

Current execution provides:

- combined-reference alignment;
- mapping rates;
- featureCounts/Salmon comparison.

Missing:

- host/pathogen/ambiguous classification script;
- per-gene coverage loss;
- mismatch diagnostics;
- decoy-aware host/pathogen quantification;
- variant-aware/WASP or reference-swap sensitivity.

Either implement these or rename the output “mapping diagnostics,” not mapping-bias correction.

## 6.5 Pathway script contract is incomplete

The planned script receives:

- ranked statistics;
- orthology;
- gene sets.

This supports fgsea. It does not support `camera`, which also needs expression, design, and contrast.

Recommendation:

- primary: fgsea on signed interaction statistics;
- sensitivity: separate camera script with expression/design/contrast;
- define the exact multiplicity family;
- freeze collection versions/checksums/licenses.

## 6.6 Network gate needs executable criteria

The execution plan lists:

- robust network;
- bootstrap;
- preservation.

It does not specify:

- number of bootstraps;
- membership-stability threshold;
- eigengene test threshold;
- external module-score procedure;
- failure behavior.

Add the quantitative criteria from Layer 5.

## 6.7 Motif workflow has missing inputs/outputs

Commands assume:

- `primary_gene_set.fa`;
- `matched_background.fa`;
- JASPAR MEME file.

The plan does not generate them.

Also missing:

- repeated-background aggregation;
- random seeds;
- 1-kb/2-kb multiplicity;
- FIMO step despite planned site tables;
- TF-expression filtering;
- external frozen-motif tests.

Add these or remove unsupported motif-site/network claims.

## 6.8 The small-RNA branch is incomplete

PRJNA922965 is downloaded, but the execution plan lacks:

- small-RNA adapter trimming;
- miRNA quantification;
- differential analysis;
- pairing verification;
- target prediction;
- miRNA/mRNA integration.

Either:

- implement a separate optional branch; or
- remove PRJNA922965 from the active execution plan.

It must not pass through the long-RNA workflow.

## 6.9 Candidate rules must be deterministic

Current Tier A/B/C definitions lack:

- exact thresholds;
- missing-data treatment;
- conflict resolution;
- tie handling;
- minimum evidence;
- empty-tier behavior.

Define the candidate universe and Boolean rules before external analysis.

## 6.10 Environment and workflow need real locking

Current package installation is unpinned.

Add:

- platform lockfile or pinned container digest;
- R/Bioconductor release lock;
- tiny synthetic fixture;
- expected output hashes;
- CI or clean-checkout integration test;
- explicit creation of `release.yaml`.

Calling `snakemake --rerun-incomplete` is not equivalent to a clean reproduction.

---

## 7. Prioritized revision list

## P0 — Must change before analyzing outcomes

1. Add discovery/validation firewall.
2. Add Stage 0 preflight and repair missing-asset assumptions.
3. Freeze candidate/signature/pathway rules before external data.
4. Designate GSE262200 as either development data or untouched holdout.
5. Add biological-unit eligibility gate.
6. Choose one matched reference/identifier bundle.
7. Define a specific new discovery hypothesis.
8. Add quantitative validation criteria and vocabulary.

## P1 — Required for credible claims

1. Add an estimand registry and restrict meta-analysis.
2. Implement exact mapping-bias analysis or narrow the claim.
3. Complete pathway input contracts.
4. Add quantitative network/motif gates.
5. Implement or remove the small-RNA branch.
6. Make candidate ranking deterministic.
7. Make title/figures conditional on outcomes.

## P2 — Required for release quality

1. Pin environments/containers.
2. Add synthetic fixtures and clean-run tests.
3. Add resource acquisition/checksum/license records.
4. Add retrospective-protocol amendment log.
5. Add a claim-to-source novelty matrix.

---

## 8. Recommended revised paper architecture

## Primary discovery

> Genome-wide Guiwei–Yurong cultivar×infection interaction and a frozen signed response signature.

## Internal robustness

> The same discovery survives alternative quantification, statistical methods, filtering, leave-one-out analysis, and mapping sensitivity.

## External evaluation

> The frozen signature shows prespecified directional transport to the Guiwei–Heiye fruit time course and generic infection/tissue contexts.

## Secondary discovery

Choose one:

- differential transcript usage; or
- carefully qualified host–pathogen read dynamics.

## Orthogonal support

Use:

- small-RNA coherence;
- independent annotation evidence;
- published independent-material evidence.

## Final claim

A defensible final claim would be:

> A genome-wide interaction analysis identifies a robust cultivar-dependent lychee infection-response signature that shows cross-context support across independent public datasets.

This is stronger and more precise than:

- “regulatory architecture”;
- “validated resistance genes”;
- “functional cis-elements.”

---

## 9. Final assessment

### Discovery readiness

Current rating: **moderate, not yet sufficient**.

Reason:

- interaction analysis may be novel;
- no single biological discovery hypothesis is yet locked;
- prior-art collision remains likely;
- the workflow can still end as a cleaner reanalysis.

### Validation readiness

Current rating: **weak-to-moderate**.

Reason:

- robust same-data sensitivity is planned;
- public cross-context datasets are available;
- no direct replication dataset is currently confirmed;
- external outcomes are not held out;
- quantitative acceptance criteria are missing.

### Execution readiness

Current rating: **moderate after revision**.

Reason:

- commands and stage structure are strong;
- several assumed assets/scripts/resources are currently absent;
- pathway, motif, small-RNA, mapping-bias, and candidate-ranking contracts are incomplete.

### Overall recommendation

Revise both plans before running outcome analyses.

The most important change is not adding more tools. It is enforcing a prospective discovery/validation design:

1. freeze discovery rules;
2. discover on GSE201243;
3. freeze results;
4. evaluate untouched external datasets with fixed criteria;
5. report robustness, replication, cross-context support, and orthogonal support separately.

That structure gives the computational-only paper its best chance of containing both a new discovery and credible validation.
