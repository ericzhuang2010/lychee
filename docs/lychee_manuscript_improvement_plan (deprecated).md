# Computational-Only Improvement Plan for the Lychee–*Phytophthora litchii* Manuscript

## Scope and claim boundary

This revision assumes that no new biological samples or laboratory assays can be generated. The paper must therefore be repositioned as a rigorous, transparent reanalysis and public-data integration study.

The pathogen’s current accepted name is *Phytophthora litchii*; *Peronophythora litchii* is a widely used synonym. Introduce both at first mention and then use *P. litchii*. Preserve historical names inside quoted titles and repository metadata.

The revised paper can support:

- genome-wide cultivar-by-infection statistics;
- independent public-data consistency;
- time- and tissue-dependent expression patterns;
- corrected gene annotation;
- formal pathway and gene-set results;
- exploratory coexpression modules;
- statistically enriched candidate promoter motifs;
- a reproducible candidate-prioritization resource.

It cannot support:

- a demonstrated resistance mechanism;
- functional cis-regulatory elements;
- direct TF–target regulation;
- causal resistance genes;
- general resistance-class claims from one cultivar per class.

The title, abstract, results, discussion, and conclusions must remain inside those limits.

---

## 1. Required scientific pivot

### 1.1 Replace the current central claim

Current framing such as “regulatory architectures” is too strong for public transcriptomics and motif prediction.

Recommended central question:

> Which lychee genes and pathways show statistically supported cultivar-dependent infection responses, and which findings remain consistent across independent public datasets, tissues, cultivars, and time points?

Recommended thesis:

> Public lychee datasets support a reproducible, uncertainty-aware ranking of cultivar-dependent infection responses and pathways, while functional regulatory and resistance mechanisms remain hypotheses.

### 1.2 Define the novelty correctly

GSE201243 has already supported at least two gene-family studies:

- LcCDPK study: [https://doi.org/10.13925/j.cnki.gsxb.20220307](https://doi.org/10.13925/j.cnki.gsxb.20220307)
- LcWRKY study: [https://doi.org/10.1002/agj2.21435](https://doi.org/10.1002/agj2.21435)

Novelty must not be “discovering that Guiwei and Yurong respond differently.” It should come from:

1. the first complete FDR-controlled genome-wide interaction analysis of this accession;
2. reprocessing multiple public studies against one frozen modern reference;
3. explicit mapping-bias and metadata-provenance audits;
4. time-course and tissue integration;
5. corrected annotations and full result release;
6. formal ranked pathway and motif analysis;
7. transparent evidence grading and negative-result reporting.

### 1.3 Replace selected-gene arithmetic with genome-wide inference

The current calculation:

`log2FC(Yurong infected/mock) - log2FC(Guiwei infected/mock)`

is an interaction effect size, but the manuscript applies it only to 18 preselected genes and does not report gene-wise uncertainty or FDR.

Required correction:

- fit the factorial model to every adequately expressed gene;
- report interaction log2FC, SE, statistic, P, and BH q;
- use the old 18 only as an audit set;
- release complete all-gene tables;
- report if no interaction survives q<0.05.

### 1.4 Replace metadata PCA with expression QC

PCA of spot count, file size, and total bases is not biological expression QC.

Required:

- VST/rlog PCA;
- sample-distance heatmap;
- replicate correlations;
- detected-gene count;
- mapping, mismatch, duplication, strandedness, and gene-body coverage;
- Cook’s distance/influence;
- pathogen-read fraction;
- documented exclusion criteria and sensitivity analyses.

### 1.5 Remove biologically unmotivated analyses

Remove or demote:

- chromosome locations of 18 unrelated genes;
- exon–intron comparisons across unrelated genes;
- MEME protein motifs across unrelated proteins;
- raw PlantCARE motif-count figures;
- descriptive Reactome themes without statistics.

Retain a family-level structural analysis only if the genes are demonstrably homologous and the analysis answers a stated question.

### 1.6 Correct candidate annotations

Audit all old candidates from the actual frozen protein models.

Priority corrections:

- LITCHI017676 is provisionally a CCoAOMT-like, SAM-dependent phenolic O-methyltransferase; the current polyamine-pathway interpretation is unsupported.
- LITCHI019299 appears to contain an AdoMetDC regulatory-leader/uORF model rather than encoding the catalytic enzyme; retire the enzymatic claim until resolved.

Supporting source:

- [https://doi.org/10.3389/fgene.2024.1360138](https://doi.org/10.3389/fgene.2024.1360138)

### 1.7 Reframe promoter results

Computational motif analysis can identify statistical sequence enrichment only.

Required changes:

- call results “candidate TF-binding motifs”;
- use real, matched lychee promoters as background;
- use PWMs rather than exact PlantCARE strings;
- require the corresponding TF family to be expressed;
- report motif-level FDR and enrichment effect size;
- do not claim binding, activation, hormone signaling, or functional cis-elements.

### 1.8 Reframe resistance language

With one genotype representing each resistance label:

- say “Guiwei–Yurong difference,” not a general susceptible–resistant mechanism;
- say “resistance-associated candidate,” not resistance gene;
- do not equate more DEGs with stronger defense;
- distinguish baseline genotype effects from infection interactions;
- treat Heiye and Feizixiao results as cross-context evidence.

---

## 2. Public datasets and reference resources

## 2.1 Primary dataset: GSE201243 / PRJNA830488

Sources:

- [GEO GSE201243](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE201243)
- [ENA PRJNA830488](https://www.ebi.ac.uk/ena/browser/view/PRJNA830488)

Design:

- Guiwei and Yurong1 leaves;
- pathogen challenge and sterile-water mock;
- 24 h;
- three deposited libraries per cell;
- 12 paired-end runs;
- SRR18856598–SRR18856609.

Use:

- primary genome-wide cultivar×infection test;
- within-cultivar infection effects;
- expression QC;
- mapping-bias assessment.

Caveats:

- repository and associated-paper instrument/method descriptions conflict;
- source-tree independence is undocumented;
- no deposited integer-count matrix.

Use repository records as the sequencing manifest and explicitly report unresolved provenance.

## 2.2 Time-course dataset: PRJNA450886

Sources:

- [BioProject PRJNA450886](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA450886)
- [paper](https://doi.org/10.1038/s41598-019-39100-w)

Design:

- Guiwei and Heiye mature-fruit pericarp;
- mock and inoculated;
- 6, 24, and 48 h;
- three deposited libraries per cell;
- 36 paired-end runs;
- SRR8297698–SRR8297733.

Use:

- cultivar×infection×time inference;
- temporal expression trajectories;
- pathway consistency;
- exploratory network discovery.

Caveats:

- fruit/Heiye is not direct replication of Yurong leaves;
- source-tree independence is unclear;
- analyze separately and label cross-context evidence.

## 2.3 Tissue dataset: GSE222651 / PRJNA922966

Sources:

- [GEO GSE222651](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222651)
- [superseries GSE222652](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222652)
- [ENA PRJNA922966](https://www.ebi.ac.uk/ena/browser/view/PRJNA922966)

Design:

- Feizixiao leaves and fruits;
- challenge (`C`) and mock (`M`);
- 24 h;
- three deposited libraries per cell;
- 12 paired-end long-RNA libraries;
- SRR23050939–SRR23050950.

Use:

- infection effects by tissue;
- tissue×infection interaction;
- cross-tissue pathway and candidate consistency.

## 2.4 Parallel small-RNA dataset: GSE222650 / PRJNA922965

Sources:

- [GEO GSE222650](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222650)
- [ENA PRJNA922965](https://www.ebi.ac.uk/ena/browser/view/PRJNA922965)

Design:

- corresponding labels and nominal design to GSE222651;
- 12 single-end miRNA libraries;
- SRR23050908–SRR23050919.

Use only when:

- biological specimen pairing is confirmed;
- miRNA passes FDR;
- target complementarity is stringent;
- mRNA direction is compatible.

Do not present a predicted ceRNA network as causal regulation.

## 2.5 Quick-start dataset: GSE262200 / PRJNA1090613

Sources:

- [GEO GSE262200](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262200)
- [BioProject PRJNA1090613](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1090613)

Design:

- Guiwei and genotype `SFZ` leaves;
- pathogen/mock;
- three deposited libraries per cell;
- 12 paired-end runs;
- SRR28413505–SRR28413516;
- deposited integer-count matrix.

Use:

- immediate validation of the interaction-analysis code;
- external candidate sensitivity;
- pipeline prototyping.

Hard limitations:

- sampling time is not reported;
- SFZ full name and phenotype are not documented;
- no linked peer-reviewed publication was found.

Do not call it resistant-versus-susceptible validation without clarification.

## 2.6 Registered but unavailable data

PRJNA1195217 is associated with the 2025 lignin/ROS paper but had no public BioSamples/runs at the search cutoff. Monitor it; do not list it as downloadable evidence.

## 2.7 Host reference

Use:

- SCAU_Lch_v2.0, GCA_019925255.1;
- external matching `LITCHI` annotation from the publication/Sapindaceae package;
- Mendeley DOI 10.17632/kggzfwpdr9.1 for a redistributable assembly/annotation package.

Before use:

- reconcile FASTA/GFF chromosome names and lengths;
- compare checksums where possible;
- freeze FASTA, GFF3, CDS, protein, transcript files;
- define canonical transcripts;
- record release/retrieval date;
- do not mix versions.

## 2.8 Pathogen reference

Use GWHAOTU00000000/GWHAOTU00000000.1 for competitive host–pathogen mapping. Preserve strain/version provenance.

Use pathogen-read fraction as an exploratory colonization proxy only. These libraries were not designed as balanced dual RNA-seq, so do not force pathogen differential-expression analysis when depth is inadequate.

---

## 3. Computational analyses

## 3.1 Reproducibility audit

Goal:

Determine which current numbers and figures can be regenerated before adding new analyses.

Actions:

1. reconstruct all sample sheets from repository records;
2. reproduce the legacy pipeline only as a benchmark;
3. verify 17 Guiwei and 117 Yurong DEGs;
4. audit every old candidate annotation;
5. reproduce promoter-background values and exact motif strings;
6. identify current figures without source data/scripts;
7. classify every result as reproduced, changed, or not reproducible.

Outputs:

- immutable manifests/checksums;
- current-claim audit table;
- corrected old-18 annotation table;
- figure disposition list;
- metadata-conflict report.

## 3.2 Uniform modern read processing

Pipeline:

1. raw FastQC/MultiQC;
2. evidence-based adapter trimming with fastp/Cutadapt;
3. empirical strandedness;
4. combined host–pathogen reference;
5. STAR/HISAT2 alignment;
6. featureCounts host gene counts;
7. Salmon/tximport sensitivity quantification;
8. RSeQC gene-body/read-distribution metrics;
9. host/pathogen/ambiguous read fractions.

Filtering:

- define before viewing interaction P values;
- e.g. ≥10 counts in at least the smallest cell size;
- report a CPM-filter sensitivity;
- never filter by old-candidate status or fold change.

Mapping-bias audit:

- mapping and mismatch rate by cultivar;
- coverage uniformity;
- genes with cultivar-specific coverage loss;
- candidate loci in polymorphic regions;
- variant-aware/pseudoalignment sensitivity for leading candidates.

Outputs:

- raw and filtered count matrices;
- transcript estimates;
- final MultiQC;
- mapping-bias report;
- featureCounts/Salmon concordance;
- locked environment.

## 3.3 Primary genome-wide interaction

DESeq2 model:

```r
design = ~ cultivar + treatment + cultivar:treatment
```

Primary interaction:

`infection effect in Yurong - infection effect in Guiwei`

Tests:

- Wald interaction for all filtered genes;
- full-versus-reduced LRT;
- within-Guiwei infection;
- within-Yurong infection;
- appropriate LFC shrinkage for display;
- leave-one-library-out stability;
- alternate quantifier/filter sensitivity.

Required reporting:

- base mean;
- interaction LFC and SE;
- statistic, P, BH q;
- tested gene count;
- independent-filter threshold;
- all normalized counts for plotted genes.

Decision:

- q<0.05 defines statistical interaction evidence;
- no surviving genes is a valid result;
- do not replace it with selected-gene raw P values.

## 3.4 PRJNA450886 time-course analysis

Model:

```r
design = ~ cultivar * treatment * time
```

Global test:

- full model with three-way interaction;
- reduced model containing main effects and all two-way terms.

Contrasts:

- infection within each cultivar/time;
- cultivar×infection at 6, 24, 48 h;
- interaction changes over time;
- time-matched mock cultivar differences.

Sensitivity:

- edgeR quasi-likelihood or limma-voom;
- old unigene-to-`LITCHI` mapping;
- leave-one-library-out where feasible.

Interpretation:

- time-course, fruit, and Heiye evidence is partial/cross-context;
- do not call it direct replication of the Yurong leaf interaction.

## 3.5 GSE222651 tissue analysis

Model:

```r
design = ~ tissue + treatment + tissue:treatment
```

Estimate:

- leaf infection;
- fruit infection;
- tissue×infection;
- candidate/pathway consistency.

Classify findings as common, leaf-enriched, fruit-enriched, or context-specific.

## 3.6 GSE262200 quick interaction

Model:

```r
design = ~ genotype + treatment + genotype:treatment
```

Use the deposited count matrix to test the analysis scripts quickly.

Until metadata are clarified:

- call groups GW and SFZ only;
- do not assign a resistance interpretation;
- do not compare effect timing.

## 3.7 Cross-study integration

Do not merge raw counts across studies.

Instead:

1. process against one frozen host annotation;
2. calculate within-study effects/SEs;
3. map stable `LITCHI` IDs;
4. compare signed ranks and confidence intervals;
5. quantify direction concordance;
6. use random-effects meta-analysis only for comparable contrasts;
7. report heterogeneity;
8. run leave-one-study-out sensitivity.

Evidence labels:

- direct replication;
- partial replication;
- pathway-level consistency;
- not replicated;
- not testable.

Because no independent study exactly duplicates Guiwei/Yurong leaves at 24 h with known source units, most public evidence will be partial rather than direct.

## 3.8 Annotation and orthology

For every expressed gene:

- select canonical protein by a documented rule;
- InterPro/Pfam/GO;
- eggNOG;
- reviewed plant Swiss-Prot hits;
- TAIR12 and named rice-release homologs;
- reciprocal-best-hit/OrthoFinder groups;
- PlantTFDB/iTAK classification;
- signal peptide/transmembrane/low-complexity where relevant.

For each old candidate:

- verify sequence/model;
- distinguish paralogs;
- check uniquely mappable regions;
- resolve conflicting labels;
- combine annotation with interaction and replication evidence.

Release the full mapping and unmapped fraction.

## 3.9 Ranked pathway analysis

Primary:

- signed full-model statistic;
- fgsea/camera or equivalent;
- one prespecified primary collection and contrast;
- hierarchical/global FDR.

Secondary:

- ORA on statistically defined sets;
- background = all testable expressed genes.

Collections:

- GO;
- KEGG KO pathways;
- MapMan/Mercator bins;
- Plant Reactome orthology;
- curated immunity, hormone, ROS, cell-wall, calcium, and proteostasis sets.

Requirements:

- set size/mapped fraction;
- one-to-many orthology handling;
- leading-edge genes;
- enrichment direction;
- all tested families;
- redundant-term reduction.

## 3.10 Exploratory network analysis

Do not run WGCNA on 12 GSE201243 samples.

Use PRJNA450886 only after provenance review:

- signed robust network;
- data-driven soft threshold;
- minimum module size around 30;
- source-unit-aware bootstrap;
- factorial model on eigengenes;
- condition-stratified sensitivity;
- module-score/preservation checks in other studies.

Call modules exploratory. A cultivar-correlated module is not resistance-associated without an infection interaction and independent consistency.

## 3.11 Rigorous in-silico promoter analysis

Promoters:

- derive from frozen genome/GFF;
- use a stated interval such as 2 kb upstream/+200 bp;
- strand-aware;
- truncate boundaries;
- mark upstream-gene overlap;
- state whether a true TSS or only gene/CDS start is available.

Motif analysis:

- JASPAR/CIS-BP/DAP-seq plant PWMs;
- AME enrichment;
- real expressed-gene promoter backgrounds;
- matching on length, GC, expression, and chromosome where possible;
- repeated background sampling;
- STREME de novo discovery;
- Tomtom motif matching;
- FIMO only after set-level enrichment;
- motif-level FDR and effect size.

Interpretation:

- report candidate TF-binding motifs;
- require the cognate TF family to be expressed;
- do not claim binding, occupancy, activation, or functional promoter regulation.

## 3.12 Candidate-prioritization framework

Score each candidate on:

1. annotation confidence;
2. genome-wide interaction q/effect;
3. counts and leave-one-out stability;
4. temporal evidence;
5. cross-context consistency;
6. pathway/module evidence;
7. TF/motif coherence;
8. novelty;
9. reference-bias risk.

Output tiers:

- Tier A: strongest statistically supported computational candidates;
- Tier B: stable cross-context/pathway candidates;
- Tier C: exploratory or weakly annotated;
- retired: model/annotation/statistical failure.

Do not label any tier “validated resistance genes.”

## 3.13 Reproducibility package

Implement Snakemake/Nextflow with:

- versioned inputs/checksums;
- containers/environments;
- manifest generation;
- download/QC/alignment/counting;
- all statistical contrasts;
- figures/tables;
- fixed seeds;
- automatic report.

Release:

- complete manifests;
- counts and all-gene results;
- annotation/orthology;
- pathways/networks/motifs;
- candidate matrix;
- plotted numeric data;
- scripts/environments/README.

The larger local archive at `/Users/rzhuang/Documents/research/lychee` contains manuscript history, figure exports, S2 templates, and an S3 GSE262200 workflow, but it does not contain the complete raw-to-result evidence trail. Treat those scripts as templates until rerun outputs match the paper.

---

## 4. Figures and tables

## 4.1 Main figures

### Figure 1 — Study designs, provenance, and transcriptomic QC

Panels:

- public-study design map;
- accession/sample counts;
- metadata conflicts;
- per-study expression PCA;
- sample-distance/replicate plots;
- mapping and detected-gene metrics.

Purpose:

Replace metadata-depth PCA and show whether the expression data support inference.

### Figure 2 — Genome-wide GSE201243 interaction

Panels:

- interaction MA/volcano with q;
- Guiwei versus Yurong infection effects;
- top interaction forest plot;
- normalized counts for leading genes;
- old-18 audit labels.

Purpose:

Directly address reviewer concerns about selected-gene bias and missing FDR.

### Figure 3 — Time-course and cross-study consistency

Panels:

- Guiwei/Heiye trajectories;
- time-specific interaction effects;
- cross-study forest plots;
- sign concordance;
- explicit evidence-grade labels.

### Figure 4 — Ranked pathway results

Panels:

- normalized enrichment scores across studies;
- leading-edge genes;
- pathway-direction comparison;
- mapping/unmapped summary.

### Figure 5 — Exploratory modules and candidates

Panels:

- module eigengene factorial effects;
- module trajectories;
- pathway/motif enrichment;
- compact predicted TF–target network;
- bootstrap/preservation evidence.

Label the network predicted and exploratory.

### Figure 6 — Promoter motif enrichment

Panels:

- matched-background design;
- enriched PWMs with q/effect sizes;
- distance-to-start distribution;
- motif occurrence in ranked candidates;
- sensitivity across promoter windows/background draws.

Do not imply functional promoter activity.

### Figure 7 — Final evidence-ranked candidate resource

Panels:

- candidate evidence heatmap;
- annotation confidence;
- interaction/time/cross-study support;
- reference-bias flags;
- final evidence tiers.

## 4.2 Main tables

### Table 1 — Dataset inventory

Include:

- accession;
- cultivar/genotype;
- resistance-label evidence;
- tissue/time/treatment;
- deposited replicates;
- source-unit provenance;
- library details;
- use and limitation.

### Table 2 — Genome-wide interaction results

Include:

- gene/transcript ID;
- annotation;
- base mean;
- within-cultivar infection effects;
- interaction effect/SE/P/q;
- stability;
- mapping-bias flag.

### Table 3 — Cross-study evidence

Include:

- effects and uncertainty by study;
- tissue/cultivar/time;
- heterogeneity;
- evidence label.

### Table 4 — Pathways

Include:

- collection/pathway;
- set size/mapped fraction;
- NES/effect;
- P/q;
- leading-edge genes;
- studies supporting the result.

### Table 5 — Candidate evidence matrix

Include all prioritization criteria, final tier, and reason selected/retired.

## 4.3 Supplementary outputs

- S1 complete metadata/checksums/conflicts;
- S2 per-library QC;
- S3 all DE/interaction results;
- S4 transcript/gene/unigene mapping;
- S5 annotation/orthology;
- S6 all pathway tests/backgrounds;
- S7 network membership/bootstrap;
- S8 motif enrichment/FIMO sites;
- S9 candidate evidence matrix;
- S10 software versions/commands;
- complete model diagnostics and sensitivity figures.

## 4.4 Figure-generation requirements

Every figure must:

- be generated from a script;
- write the plotted numeric data;
- use consistent identifiers and colors;
- show q rather than raw P where appropriate;
- include uncertainty;
- avoid manual value editing;
- export vector PDF/SVG and journal-required TIFF.

---

## 5. Manuscript restructuring

## 5.1 Recommended title

Example:

> Genome-wide interaction and cross-study transcriptomic reanalysis prioritize cultivar-dependent lychee responses to *Phytophthora litchii*

Avoid:

- “regulatory architecture”;
- “mechanism”;
- “functional cis-elements”;
- “resistance genes.”

## 5.2 Abstract

Include:

- public datasets and sample designs;
- genome-wide interaction model;
- whether interaction genes pass FDR;
- independent time/tissue consistency;
- pathway and candidate evidence;
- explicit computational-only limitation.

Do not state that motifs drive expression.

## 5.3 Introduction

Five-paragraph flow:

1. disease relevance and taxonomy;
2. known cultivar/pathosystem work;
3. prior use of GSE201243;
4. unresolved statistical/reproducibility gap;
5. study aims and claim boundary.

## 5.4 Results order

1. provenance and expression QC;
2. genome-wide interaction;
3. time-course reanalysis;
4. tissue and additional-genotype analyses;
5. cross-study consistency;
6. annotation and pathway results;
7. exploratory network/motif results;
8. evidence-ranked candidate resource.

## 5.5 Discussion

Structure:

1. principal statistically supported result;
2. timing and context dependence;
3. agreement/disagreement with lychee literature;
4. pathway-level interpretation;
5. why more DEGs do not prove stronger defense;
6. candidate utility and uncertainty;
7. mapping/provenance/sample-size limitations;
8. causal questions that cannot be resolved from the available public data.

## 5.6 Methods

Report:

- accession/run mapping;
- metadata conflicts and inference rules;
- genome/annotation checksums;
- processing parameters;
- strandedness;
- count filtering;
- all model formulas and contrasts;
- FDR strategy;
- orthology handling;
- network stability;
- promoter/background definitions;
- software versions;
- code/data repository.

## 5.7 Conclusions

Conclude with:

- what is statistically supported;
- what replicates partially or at pathway level;
- which candidates are prioritized;
- what remains unvalidated.

Do not convert computational prioritization into causal language.

---

## 6. Computational execution sequence and timeline

## Phase 1 — Repository and provenance, weeks 1–2

Actions:

- create version-controlled structure;
- import S2/S3 templates;
- generate ENA/GEO manifests;
- download GSE262200 counts;
- inventory current figures/scripts;
- open metadata-author queries.

Gate:

- provisional master manifest;
- reproducibility audit;
- analysis environment locked.

## Phase 2 — Primary raw-data analysis, weeks 2–6

Actions:

- download/checksum GSE201243;
- freeze compatible host/pathogen references;
- raw QC, trimming, alignment, counting;
- expression QC and mapping-bias audit;
- genome-wide interaction and sensitivity.

Gate:

- complete all-gene interaction table;
- no unresolved technical failure;
- current 18 audited.

## Phase 3 — Independent public-data reanalysis, weeks 5–10

Actions:

- process PRJNA450886;
- process GSE222651;
- run GSE262200 count analysis;
- optionally process small RNA;
- produce per-study all-gene results.

Gate:

- each study has complete QC/results;
- contexts and provenance limitations recorded.

## Phase 4 — Integration and interpretation, weeks 9–14

Actions:

- orthology and corrected annotation;
- ranked pathways;
- cross-study effect integration;
- exploratory network;
- rigorous motif enrichment;
- candidate evidence matrix.

Gate:

- claims are supported by multiple computational evidence types;
- no mechanism language;
- negative/inconsistent results retained.

## Phase 5 — Figures, paper, and release, weeks 13–18

Actions:

- script all figures/tables;
- rewrite manuscript;
- release counts/results/code;
- reproduce in a clean environment;
- internal statistical and domain review;
- select a journal appropriate for a computational reanalysis/resource.

Gate:

- all outputs regenerate;
- all accessions resolve;
- title/abstract obey the claim boundary.

Estimated duration: approximately 4–5 months, depending on downloads, compute, metadata clarification, and annotation-resource setup.

---

## 7. Decision gates

### Gate 1 — Can the current result be reproduced?

If no:

- investigate inputs, versions, and sample mapping;
- report discrepancies;
- do not preserve legacy numbers for continuity.

### Gate 2 — Does any genome-wide interaction survive FDR?

If yes:

- prioritize stable interactions.

If no:

- report the null;
- focus on effect uncertainty and pathway-level patterns;
- do not use selected raw P values.

### Gate 3 — Are public datasets sufficiently comparable?

If no:

- use cross-context consistency labels;
- avoid meta-analysis;
- report heterogeneity descriptively and statistically where possible.

### Gate 4 — Is the network stable?

If no:

- remove it from the main paper;
- retain only robust pathway and gene-level analyses.

### Gate 5 — Are promoter motifs robust to background/window choices?

If no:

- remove motif claims;
- retain promoter analysis as a negative sensitivity result.

### Gate 6 — Is the revised contribution sufficiently novel?

Evaluate against:

- prior LcCDPK/LcWRKY work;
- 2019 time course;
- 2023 ncRNA study;
- 2025 lignin/ROS study;
- 2026 peptide/WRKY work.

If the main finding duplicates prior work, reposition the paper as a reproducibility and data-resource report rather than a discovery paper.

---

## 8. Key literature benchmarks

Direct lychee:

- [2019 resistant/susceptible time course](https://doi.org/10.1038/s41598-019-39100-w)
- [2023 LcWRKY study](https://doi.org/10.1002/agj2.21435)
- [2023 ncRNA/mRNA study](https://doi.org/10.3390/agronomy13071904)
- [2025 lignin/ROS study](https://doi.org/10.1016/j.scienta.2025.114254)
- [2026 LcPIP1/LcWRKY34 study](https://doi.org/10.1021/acs.jafc.6c02163)

Computational/method precedents:

- [DESeq2](https://doi.org/10.1186/s13059-014-0550-8)
- [WGCNA](https://doi.org/10.1186/1471-2105-9-559)
- [network module preservation](https://doi.org/10.1371/journal.pcbi.1001057)
- [AME motif enrichment](https://doi.org/10.1186/1471-2105-11-165)
- [PlantPAN 4.0](https://pmc.ncbi.nlm.nih.gov/articles/PMC10767843/)
- [Arabidopsis PTI motif analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC7610817/)

Use these to justify methods and claim restraint, not to imply causal validation of the revised study.

---

## 9. Immediate next actions

1. Initialize the analysis repository and environments.
2. Import S2/S3 workflow snapshots.
3. Download GSE262200 counts and all ENA manifests.
4. Freeze the provisional sample manifest and metadata-issue log.
5. Download/checksum GSE201243 FASTQ.
6. validate the host FASTA/GFF pairing.
7. Run raw-to-count processing and real expression QC.
8. Run the genome-wide GSE201243 interaction.
9. Reanalyze PRJNA450886 and GSE222651.
10. Complete annotation, pathway, cross-study, network, and motif analyses.
11. Freeze the candidate evidence matrix.
12. Generate scripted figures/tables.
13. Rewrite the paper within the computational claim boundary.
14. Release the complete reproducibility package.
