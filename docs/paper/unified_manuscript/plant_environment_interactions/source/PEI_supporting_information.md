# Contents and file inventory

This file contains detailed methods, supplementary results, Tables S19–S20 and Figures S1–S4. A separate archive, `PEI_Supporting_Data_and_Code.zip`, contains machine-readable Tables S1–S18, source data for every figure, the registered protocol and amendment log, analysis code, Snakemake workflows, configurations, tests, metadata and environment specifications. The complete archive is also permanently available at https://zenodo.org/records/22436625.

- Methods S1: Detailed methods and reproducibility information.
- Results S1: Supplementary sensitivity, transcript-usage, orthogonal and power results.
- Table S19: Locked dataset roles and eligibility.
- Table S20: Genome-wide interaction estimates for the 18 exploratory-stage candidates.
- Figure S1: Replicate-level normalized counts.
- Figure S2: Conditional parametric power curves.
- Figure S3: Exploratory signed-signature estimate.
- Figure S4: Conditional transcript usage.

# Methods S1: Detailed Methods

## S1.1 Study design, registration and evidence vocabulary

The work had two stages. Stage 1 was an exploratory reanalysis of the GSE201243 leaf series and was completed before registration. Stage 2 was governed by a time-stamped protocol that fixed dataset roles, models, thresholds, conditional gates, empty-result behavior and evidence terminology. Protocol version 1.0.0 was frozen on 18 August 2026, and its SHA-256 hash was recorded before confirmatory expression outcomes were computed. The amendment log records 20 outcome-blind clarifications, implementation corrections and optimizations made before any discovery or external expression outcome was viewed, and three post-outcome amendments confined to technical quality control and manifest verification.

The primary external study had been published previously, and its headline biological conclusions were known to the analyst before registration. Dataset roles and thresholds were nevertheless fixed before any external count matrix was processed. Because every cohort is public, the staged external unlock is a workflow-enforced computational safeguard rather than experimental blinding.

Throughout the work, *frozen* denotes a computed result fixed at a recorded checkpoint and not subsequently modified; *discovery* refers only to the registered genome-wide cultivar-by-infection analysis in PRJNA830488; *robustness* refers only to prespecified sensitivity analyses within that cohort; and *cross-context support* denotes a passing frozen test in a cohort differing in tissue, comparator or design. Cross-context support is not described as replication. Annotation, motifs, small RNA and literature were maintained as separate orthogonal evidence classes and could not substitute for expression support.

## S1.2 Exploratory-stage analyses

The 12 GSE201243 libraries were evaluated with FastQC 0.11.9, trimmed with Trimmomatic 0.39, aligned with TopHat 2.0.12/Bowtie2 2.2.3 to the SCAU_Lch_v2.0 assembly (GCA_019925255.1), counted in union mode with HTSeq 2.0.2 and analyzed by DESeq2 1.42.0 within each cultivar. Candidate prioritization combined adjusted significance, infection-associated fold-change magnitude and annotation plausibility. Structural, conserved-motif and promoter analyses used TBtools-II 2.096, MEME 5.5.5 and PlantCARE (Anders et al., 2015; Bailey and Elkan, 1994; Bolger et al., 2014; Chen et al., 2020; Kim et al., 2013; Lescot et al., 2002).

For the initial promoter-background comparison, observed cis-element counts in the 18 candidate promoters were compared with 100,000 randomized sets of eighteen 2-kb sequences with lychee-like GC content. Exact motifs and reverse complements were scored, and one-sided empirical probabilities were adjusted by the Benjamini–Hochberg procedure. The selected-gene contrast was calculated as log2FC(Yurong1, infected versus mock) minus log2FC(Guiwei, infected versus mock). It was treated as a prioritization effect size rather than a genome-wide test.

## S1.3 Data provenance and eligibility

NCBI BioProject, Sequence Read Archive and Gene Expression Omnibus metadata were reconciled into a biological-unit registry. The historical search log was not retained, so search coverage was reconstructed retrospectively on 27 August 2026 and is not represented as prospective provenance. A broad GEO series query returned six records, a corresponding BioProject query returned seven, and a narrow SRA cross-check returned 42 experiment-level records. After collapsing the GSE222652 super-series, excluding PRJNA1157370 because it used *Colletotrichum gloeosporioides*, and excluding PRJNA268587/GSE63658 because it studied storage without *P. litchii* inoculation, the five prespecified cohorts remained.

Source-tree, pooling, harvest and extraction independence were not reported for the discovery libraries. All inferential values are therefore conditional on deposited-library independence. The primary interaction model required at least three included libraries in every cultivar–treatment cell.

## S1.4 Confirmatory preprocessing and technical quality gates

The SCAU_Lch_v2.0 host assembly and pathogen reference were combined with prefixed contig identifiers to absorb pathogen-derived reads. Paired reads were checked with FastQC, trimmed with fastp, aligned with STAR two-pass mapping, counted at gene level with featureCounts and independently quantified with Salmon. A library was excluded if fewer than 10 million read pairs survived trimming or fewer than 40% aligned uniquely. All 12 discovery libraries passed. GenMap exon-uniqueness scores and candidate-level observed-mapping checks supported the uniform and observed mapping-sensitivity gates.

## S1.5 Genome-wide discovery model

DESeq2 fitted gene counts with the design `cultivar + treatment + cultivar:treatment`, using Guiwei and mock as reference levels. The interaction coefficient estimates the difference in infected-minus-mock response between Yurong1 and Guiwei. Genes required counts of at least 10 in at least three libraries. Statistical candidates required genome-wide Benjamini–Hochberg *q*<0.05 and absolute interaction log2FC ≥log2(1.5). The registered rule tests a point null of zero and then filters the estimated effect.

Post hoc sensitivity used DESeq2 with `lfcThreshold = log2(1.5)` and `altHypothesis = greaterAbs`, together with apeglm false-sign-or-small values for the same threshold (Zhu et al., 2019). Neither sensitivity analysis modified frozen membership. Separate estimand-aligned DESeq2 models were fitted within Guiwei and Yurong1 using the same count matrix, 19,445-gene universe and genome-wide adjustment in each cultivar. Unshrunken maximum-likelihood interaction estimates are reported; apeglm-shrunken estimates were used only for the frozen signed score. Mappability and gene-model metrics were computed for every tested gene. A QC-first sensitivity analysis recomputed multiplicity adjustment over the 13,602 eligible genes.

## S1.6 Pathway and transcript-usage analyses

Plant Reactome memberships were transported to lychee through one-to-one reciprocal-best DIAMOND protein matches to rice (Buchfink et al., 2015). Pathway discovery applied the frozen interaction statistic to this mapping with camera, roast and fast gene-set enrichment analysis, supplemented by leading-edge deletion and expression/length-matched null gates (Korotkevich et al., 2021).

Differential transcript usage used Salmon transcript abundances analyzed with DRIMSeq and DEXSeq under stageR stage-wise error control. A conditional gate was registered in advance to ensure interpretable gene- and transcript-level error control. No substitute analysis was permitted if that gate failed.

## S1.7 Internal robustness gates

Each frozen gene was retested under four prespecified perturbations. The Salmon gate required direction agreement and an absolute effect difference no greater than 0.5 log2 units. The edgeR analysis used the identical design matrix and coefficient with trimmed-mean-of-M-values normalization, robust dispersion estimation and quasi-likelihood testing; it required genome-wide *q*<0.10 and direction agreement. The expression-filter gate refitted the model after a counts-per-million filter. The leave-one-library-out gate required direction agreement in all 12 refits and *q*<0.10 in at least 10. The observed mapping-sensitivity gate removed candidates whose effect depended on ambiguously mapped reads. Frozen pathways required agreement across the competitive, rotation, leading-edge-deletion and matched-null procedures.

## S1.8 External frozen evaluation

PRJNA450886 was analyzed with the design `cultivar × treatment × time`, with categorical time and 24 h as reference, so the cultivar-by-treatment term estimated the primary 24-h interaction and the three-way terms represented 6- and 48-h contrasts. The primary estimand was the resistant-minus-susceptible cultivar difference in infection response at 24 h. Candidate probabilities were adjusted across the full candidate-by-contrast family. Support required *q*<0.05, absolute log2FC ≥log2(1.5), a 95% CI excluding zero and discovery-direction agreement. Significant opposite-direction responses were recorded separately.

PRJNA922966 was modeled as `tissue + treatment + tissue:treatment` for generic-transfer tests. PRJNA1090613 outcomes were restricted to exploratory status because its metadata could not support a confirmatory role. The frozen signed score was evaluated at library level with the same family-wise adjustment.

## S1.9 Annotation, motifs, small RNA and literature

Representative proteins were selected by longest coding sequence with lexicographic tie-breaking. Reviewed Swiss-Prot DIAMOND matches, InterPro/Pfam assignments and one-to-one rice orthology formed separate annotation classes (Jones et al., 2014; The UniProt Consortium, 2023). A high-confidence label required at least two classes, at least 70% supported coverage and no architecture conflict.

Promoter analysis tested 927 JASPAR plant position-weight matrices in strand-aware 1-kb and 2-kb windows against 100 expression- and GC-matched genomic-background sets (Rauluseviciute et al., 2024). AME was primary and FIMO was the sensitivity procedure (Grant et al., 2011; McLeay and Bailey, 2010). Robustness required passage in at least 80 of 100 backgrounds in both windows, and an expressed cognate transcription factor was necessary for attribution. The frozen PmiREN archive was audited before small-RNA analysis; it contained no exact *Litchi* entry, so this evidence class was not testable and no study-derived replacement was introduced (Guo et al., 2020). Studies reusing an analyzed accession were retained as prior interpretation rather than counted as independent evidence.

A post hoc controlled comparison held the published 18-promoter totals, motif strings, scoring and multiplicity correction fixed while changing only the background. Published totals were tested against 100,000 simulated sets of eighteen 2-kb sequences at 34% GC and 100 genomic sets of eighteen promoters matched by expression and promoter-GC quintiles. The six reported motifs and one standard TCA variant, with reverse complements, were counted and adjusted across seven classes. The absent archived observed-motif table and canonical-promoter recount discrepancies were retained as provenance limitations.

## S1.10 Evidence tiers, power and reproducibility

Tier A required discovery, complete internal robustness, primary cross-context support, clean mapping and annotation, and an attributable orthogonal class. Tier B required discovery and complete internal robustness with partial or non-testable primary external evidence. Tier C was reserved for a robust and externally supported pathway. Significant direction reversals and mapping or annotation exclusions were assigned separately; empty tiers were permitted.

Power was evaluated by negative-binomial simulations using fitted gene-wise means and dispersions while preserving the four-cell discovery design and the 24-h four-cell external design. Twelve absolute interaction effects from 0 to 4 log2 units were evaluated with 100 simulations each. Discovery injected 262 targets and adjusted across 19,445 genes. External simulation injected two targets among the 177 frozen genes meeting simulation validity requirements and additionally required the prespecified sign and a 95% CI excluding zero. Dispersion estimates were treated as known during simulated refits, so the curves describe conditional parametric detection rather than population-level replication.

All stages ran under Snakemake 9.25.2. Confirmatory executables were FastQC 0.12.1, fastp 1.3.6, STAR 2.7.10b, featureCounts/Subread 2.1.1, Salmon 2.5.1, MEME Suite/AME/FIMO 5.5.9 and DIAMOND 2.2.5. The statistical environment was R 4.3.3/Bioconductor 3.18 with DESeq2 1.42.0, apeglm 1.24.0, edgeR 4.0.16, DRIMSeq 1.30.0, DEXSeq 1.48.0, stageR 1.24.0 and BiocParallel 1.36.0. GenMap 1.3.0 is recoverable from the pinned specification although its executable is absent from the reconstructed environment. The archive includes environments, synthetic fixtures, source data and an amendment log. A figure-generation script recomputes and asserts every headline count.

# Results S1: Supplementary Results

## S1.1 Discovery sensitivity and internal robustness

Of 19,445 tested genes, 277 met genome-wide *q*<0.05, 5,370 exceeded the effect threshold, and 262 met both. Uniform quality control excluded 31 candidates for exon-level mappability and 25 for gene-model ambiguity, leaving 206. Restricting adjustment to the 13,602 QC-eligible genes recovered all 206 and added 12 candidates. Eight of 262 statistical candidates passed the composite-null DESeq2 sensitivity analysis; the corresponding counts were seven of 206 QC-retained candidates, seven of 19 edgeR-gated candidates and seven of 16 fully robust candidates. The apeglm false-sign-or-small sensitivity retained 149, 113, 18 and 15 genes in those nested sets.

Among 206 frozen genes, 196 passed the independent-quantification gate, 19 passed the edgeR genome-wide gate, 205 passed the counts-per-million filter and 125 passed all leave-one-library-out refits. Eighteen satisfied all four jointly and 16 remained after mapping sensitivity. All candidate effect directions agreed between DESeq2 and edgeR; every candidate had nominal edgeR *P*<0.05, but only 19 met the registered genome-wide edgeR threshold.

Six Plant Reactome pathways met the discovery criterion: activation and assembly of the pre-replication complex, DNA replication initiation, maturation and circadian rhythm with positive enrichment, and jasmonic-acid signaling with negative enrichment. Circadian rhythm alone passed every internal pathway gate.

## S1.2 Exploratory estimand follow-up

The exploratory analysis asked whether infection changed expression within each cultivar. Estimand-aligned confirmatory fits found 13 of 18 exploratory genes significant in Guiwei and 16 in Yurong1; all 13 Guiwei genes and 15 of 16 Yurong1 genes also exceeded the prespecified effect magnitude. None met the distinct genome-wide cultivar-by-infection criterion. Table S20 reports the interaction estimates and eligibility of all 18 genes.

## S1.3 External, transcript-usage and orthogonal outcomes

Among the 184 candidates measurable in the primary external contrast, two passed all support criteria, five showed significant opposite-direction responses, 177 were below threshold and 22 candidates were not testable. Discovery and external effects had Pearson *r*=−0.05 (95% CI −0.19 to 0.10) and Spearman rho=−0.04. Ninety-five of 184 candidates shared direction. The probability of observing no overlap between the two cross-context-supported and 16 internally robust genes is 0.85 under independence.

The conditional transcript-usage gate identified 225 events across 152 genes among 15,790 tested transcripts. In the primary external study, 125 events were measurable but below threshold and 100 were not testable. Annotation incompatibilities prevented event-level testing in the generic-transfer cohort. The exploratory cohort produced four supported and five opposite-direction events, reported descriptively.

Family-level annotations were assigned to 150 candidates, leaving 56 without labels. No candidate satisfied the high-confidence two-class rule, largely because precomputed domain architectures were unavailable. Motifs passed in at most four of 100 matched backgrounds and none passed FIMO sensitivity. The PmiREN reference gate made the small-RNA class not testable. In the controlled PlantCARE comparison, MeJA-responsive, TCA and TC-rich classes remained significant when randomized-GC sequences were replaced with matched genomic promoters, whereas ARE was replaced by ABRE. These motifs remain hypotheses for direct assays.

## S1.4 Evidence tiers and conditional power

The deterministic rules assigned 12 genes to Tier B, retained 191 entities for exploratory follow-up and excluded 65 through explicit quality or direction rules. Tier A and Tier C were empty. Of 65 exclusions, 56 reflected uniform mapping or gene-model control, five were cross-context direction reversals and four had candidate-level mapping or annotation concerns.

The interpolated interaction effect required for 80% detection was 2.44 log2FC (5.4-fold) for genome-wide discovery and 2.11 log2FC (4.3-fold) for external candidate-family analysis. At a true absolute interaction effect of 1.5 log2FC, conditional detection probabilities were 62.7% and 74.0%, respectively. Seven genes measurable in the observed 184-gene external table were not simulation-fit eligible, so the simulated family contained 177 genes.

# Table S19. Locked dataset roles and eligibility

| Accession | Design | Locked role | Evidence class |
|---|---|---|---|
| PRJNA830488 (GSE201243) | Guiwei/Yurong1 leaf; mock/infected; 24 h; three libraries per cell | Discovery | Conditional inferential |
| PRJNA450886 | Guiwei/Heiye pericarp; mock/infected; 6, 24 and 48 h; three libraries per cell | Primary external evaluation | Cross-context |
| PRJNA922966 (GSE222651) | Feizixiao leaf/fruit; mock/infected; 24 h; three libraries per cell | Generic infection transfer | Cross-context |
| PRJNA922965 (GSE222650) | Feizixiao leaf/fruit small RNA; mock/infected; 24 h; three libraries per cell | Orthogonal modality | Orthogonal |
| PRJNA1090613 (GSE262200) | Guiwei/SFZ leaf; mock/infected; three libraries per cell | Exploratory only | Exploratory |

# Table S20. Genome-wide interaction estimates for the 18 exploratory-stage candidates

Effects are re-estimated Yurong1-minus-Guiwei differences in infection response on the log2 scale. Within-cultivar infection responses appear in Supporting Data Table S14. The interaction criterion was genome-wide *q*<0.05 and absolute log2FC ≥log2(1.5); none met both components.

| Gene | Exploratory annotation | Interaction log2FC (SE) | Genome-wide *q* | Mappability |
|---|---|---:|---:|---|
| LITCHI001510 | Poorly characterized responsive gene | −2.83 (0.91) | 0.080 | Pass |
| LITCHI019519 | EF-hand calcium-binding protein | −3.33 (1.14) | 0.106 | Pass |
| LITCHI019299 | S-adenosylmethionine-related protein | −1.21 (0.47) | 0.175 | Pass |
| LITCHI007102 | Phytosulfokine precursor | −0.74 (0.32) | 0.238 | Pass |
| LITCHI019183 | Plant lipid-transfer protein | +0.99 (0.45) | 0.273 | Pass |
| LITCHI028401 | Selected interaction candidate | −2.41 (1.13) | 0.281 | Not eligible |
| LITCHI012388 | Heat-shock protein 70 | −0.90 (0.49) | 0.381 | Pass |
| LITCHI001552 | Cyclase-like stress-related protein | +0.92 (0.55) | 0.430 | Pass |
| LITCHI001512 | Poorly characterized responsive gene | −1.01 (0.63) | 0.457 | Pass |
| LITCHI017676 | S-adenosylmethionine-related protein | −2.36 (1.53) | 0.478 | Pass |
| LITCHI002550 | Cytochrome P450 | +0.76 (0.96) | 0.762 | Pass |
| LITCHI028104 | Jacalin-like lectin | +1.39 (1.89) | 0.785 | Pass |
| LITCHI002793 | Osmotin/thaumatin-like protein | +0.41 (0.55) | 0.786 | Pass |
| LITCHI017995 | Metalloendoproteinase | +0.48 (0.73) | 0.812 | Pass |
| LITCHI009301 | Osmotin/thaumatin-like protein | −0.70 (1.08) | 0.816 | Not eligible |
| LITCHI025738 | Cyclase-like stress-related protein | −0.22 (0.62) | 0.908 | Pass |
| LITCHI011394 | Pathogenesis-related protein | −0.25 (0.98) | 0.940 | Pass |
| LITCHI018043 | Plant lipid-transfer protein | −0.10 (0.52) | 0.954 | Pass |

# Supplementary Figure Legends

## Figure S1. Replicate-level normalized counts

Replicate-level normalized counts for the two cross-context-supported genes, 12 Tier B genes and two exploratory highlights. Points are individual deposited libraries; bars show cultivar–treatment medians. Each cell contains three deposited libraries. GW, Guiwei; YR, Yurong1; inf., infected.

## Figure S2. Conditional parametric power curves

Parametric detection probability for cultivar-by-infection effects under genome-wide discovery and candidate-family external adjustment. Curves show the overall result and mean-expression quartiles; vertical intervals are 95% Wilson confidence intervals and the horizontal dashed line marks 80% power. Each effect size used 100 simulations.

## Figure S3. Exploratory signed-score estimate

Exploratory PRJNA1090613 signed-score estimate, shown separately because cohort metadata did not support its inclusion in confirmatory evaluation. Points are fitted estimates and bars are 95% confidence intervals.

## Figure S4. Conditional transcript usage

(A) Discovery gate and event counts. (B) External follow-up of the 225 discovery events, separated by prespecified study role. DTU, differential transcript usage.

# References cited only in Supporting Information

- Anders S, Pyl PT and Huber W (2015) HTSeq—a Python framework to work with high-throughput sequencing data. *Bioinformatics* 31: 166–169. https://doi.org/10.1093/bioinformatics/btu638
- Bailey TL and Elkan C (1994) Fitting a mixture model by expectation maximization to discover motifs in biopolymers. In: *Proceedings of the Second International Conference on Intelligent Systems for Molecular Biology*. AAAI Press, Menlo Park, pp. 28–36.
- Bolger AM, Lohse M and Usadel B (2014) Trimmomatic: a flexible trimmer for Illumina sequence data. *Bioinformatics* 30: 2114–2120. https://doi.org/10.1093/bioinformatics/btu170
- Buchfink B, Xie C and Huson DH (2015) Fast and sensitive protein alignment using DIAMOND. *Nature Methods* 12: 59–60. https://doi.org/10.1038/nmeth.3176
- Chen C, Chen H, Zhang Y, Thomas HR, Frank MH, He Y et al. (2020) TBtools: an integrative toolkit developed for interactive analyses of big biological data. *Molecular Plant* 13: 1194–1202. https://doi.org/10.1016/j.molp.2020.06.009
- Grant CE, Bailey TL and Noble WS (2011) FIMO: scanning for occurrences of a given motif. *Bioinformatics* 27: 1017–1018. https://doi.org/10.1093/bioinformatics/btr064
- Guo Z, Kuang Z, Wang Y, Zhao Y, Tao Y, Cheng C et al. (2020) PmiREN: a comprehensive encyclopedia of plant microRNAs. *Nucleic Acids Research* 48: D1114–D1121. https://doi.org/10.1093/nar/gkz894
- Jones P, Binns D, Chang HY, Fraser M, Li W, McAnulla C et al. (2014) InterProScan 5: genome-scale protein function classification. *Bioinformatics* 30: 1236–1240. https://doi.org/10.1093/bioinformatics/btu031
- Kim D, Pertea G, Trapnell C, Pimentel H, Kelley R and Salzberg SL (2013) TopHat2: accurate alignment of transcriptomes in the presence of insertions, deletions and gene fusions. *Genome Biology* 14: R36. https://doi.org/10.1186/gb-2013-14-4-r36
- Korotkevich G, Sukhov V, Budin N, Shpak B, Artyomov MN and Sergushichev A (2021) Fast gene set enrichment analysis. *bioRxiv*: 060012. https://doi.org/10.1101/060012
- Lescot M, Déhais P, Thijs G, Marchal K, Moreau Y, Van de Peer Y et al. (2002) PlantCARE, a database of plant cis-acting regulatory elements and a portal to tools for in silico analysis of promoter sequences. *Nucleic Acids Research* 30: 325–327. https://doi.org/10.1093/nar/30.1.325
- McLeay RC and Bailey TL (2010) Motif enrichment analysis: a unified framework and an evaluation on ChIP data. *BMC Bioinformatics* 11: 165. https://doi.org/10.1186/1471-2105-11-165
- Rauluseviciute I, Riudavets-Puig R, Blanc-Mathieu R, Castro-Mondragon JA, Ferenc K, Kumar V et al. (2024) JASPAR 2024: 20th anniversary of the open-access database of transcription factor binding profiles. *Nucleic Acids Research* 52: D174–D182. https://doi.org/10.1093/nar/gkad1059
- The UniProt Consortium (2023) UniProt: the Universal Protein Knowledgebase in 2023. *Nucleic Acids Research* 51: D523–D531. https://doi.org/10.1093/nar/gkac1052
- Zhu A, Ibrahim JG and Love MI (2019) Heavy-tailed prior distributions for sequence count data: removing the noise and preserving large differences. *Bioinformatics* 35: 2084–2092. https://doi.org/10.1093/bioinformatics/bty895
