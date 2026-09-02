# Reviewer report

**Manuscript:** *Cultivar-dependent transcriptional responses of lychee (Litchi chinensis) to Peronophythora litchii: from exploratory candidate discovery to a prospectively registered genome-wide validation*

**Recommendation: Major revision**

## Overall assessment

This is an unusually thoughtful and transparent computational reanalysis. The manuscript makes several valuable choices that are still uncommon in transcriptomics studies: it distinguishes exploratory analysis from formal inference, prospectively fixes dataset roles and terminology, separates internal robustness from external support, and reports null, contradictory, and non-testable outcomes rather than presenting only positive findings.

The manuscript is also commendably candid that the public datasets are small, that biological-replicate independence is uncertain, that no same-context replication dataset exists, and that no candidate has been experimentally tested.

Nevertheless, several central claims are currently stronger than the analyses support. In particular:

- “Genome-wide validation” is not an accurate description of the external analysis.
- The audit of the original 18 candidates tests a different estimand from the one used to select many of those candidates.
- The large discrepancy between DESeq2 and edgeR requires much deeper investigation.
- The zero overlap between internally robust and externally supported genes does not demonstrate that those properties are independent.
- The comparison between the exploratory and confirmatory promoter analyses does not isolate background selection as the cause of the different results.
- The tiering system sometimes treats cross-context nontransport as evidence against a valid context-specific discovery.
- Important statistical and computational details are deferred to supplementary materials or an unspecified repository.

I see a publishable core here, particularly as a methodological case study or transcriptomic resource, but substantial reframing and additional analysis are needed.

## Major comments

### 1. The title and central framing overstate “validation”

The manuscript itself appropriately describes PRJNA450886 as a **cross-context evaluation**, not a replication, because it differs from discovery in tissue, cultivar comparator, and time-course structure. External tests are also restricted to the frozen candidate family rather than being genome-wide in the external cohort.

Therefore, the title phrase “prospectively registered genome-wide validation” is potentially misleading in two ways:

1. The genome-wide component is the discovery analysis, not the external validation.
2. The external analysis is deliberately cross-context and cannot validate the original leaf interaction in the usual replication sense.

A more accurate title would be along the lines of:

> *Prospectively registered genome-wide analysis and cross-context evaluation of cultivar-dependent transcriptional responses of lychee to Peronophythora litchii*

Throughout the abstract, Results, Discussion, and Conclusions, I recommend consistently using:

- “statistical candidates” rather than “validated genes” or, in many places, “discoveries”;
- “cross-context support” rather than “validation”;
- “method-robust within the discovery cohort” rather than simply “robust”;
- “not supported for cross-context transport” rather than “retired,” where mapping or annotation failure is not involved.

The authors already establish a careful evidence vocabulary in Methods; the title and broad conclusions should follow the same restraint.

### 2. The preregistration chronology and prior knowledge need fuller documentation

The confirmatory protocol was registered after the author had already analyzed the discovery dataset in the exploratory stage. In addition, the primary external dataset had already been published and is cited for its biological conclusions. This does not invalidate the approach, but it means the study is not equivalent to a blinded prospective experiment.

Please provide:

- The exact registration date and a permanent DOI or immutable archive.
- The protocol version and cryptographic hash used before each analysis stage.
- A clear chronology of exploratory analysis, protocol registration, discovery reanalysis, candidate freeze, external-data access, and amendments.
- A statement of what the analyst already knew about each external study, including published gene-level or pathway-level findings.
- The search and eligibility procedure used to identify the five public cohorts, including all excluded datasets and reasons for exclusion.
- A clear indication of which amendments occurred before versus after observing discovery or external results.

Because these are public datasets, phrases such as “before the external outcome was opened” and “external unlock” describe a computational safeguard, not genuine blinding. That distinction should be explicit.

### 3. The formal audit of the original 18 candidates changes the biological estimand

The exploratory stage identified genes through within-cultivar infected-versus-mock differential-expression analyses and then prioritized 18 genes using significance, fold-change magnitude, and defense-related annotation. Only a subset was highlighted using a selected-gene comparison of cultivar responses.

The formal audit, however, evaluates all 18 exclusively against a genome-wide cultivar-by-infection interaction test. A gene can have a reproducible infection response in both cultivars while having no interaction. Conversely, differing within-cultivar significance does not establish an interaction. The manuscript recognizes the second point, but the headline statement that none of the original candidates “survived” risks implying that their original infection-response claims were directly disproven.

The audit should be divided into two distinct questions:

1. **Original infection-response claims:** Under the confirmatory preprocessing pipeline, do the 18 genes retain infected-versus-mock effects within Guiwei and/or Yurong1? These tests should use the appropriate multiplicity family.
2. **Cultivar-dependent response claims:** Which genes show a genome-wide-supported cultivar-by-infection interaction?

For genes originally described specifically as cultivar-skewed, the interaction test is the correct audit. For genes selected primarily because they were infection-responsive and biologically plausible, interaction significance is not the only relevant test.

Without this additional analysis, statements such as “none of the 18 exploratory candidates survived genome-wide inference” should be replaced by the narrower statement:

> None of the 18 candidates met the newly applied genome-wide cultivar-by-infection interaction criterion.

The broader claims about effect-size prominence and statistical reproducibility should also be moderated because the comparison involves both a new model and, in several cases, a new scientific question.

### 4. The DESeq2–edgeR discrepancy is a central result and requires much deeper analysis

Of 206 QC-retained DESeq2 candidates, 196 pass the alternative quantification gate, 205 pass the expression-filter gate, and 125 pass all leave-one-library-out fits, but only **19** pass the edgeR gate. Only 16 survive the complete conjunction.

This degree of disagreement between two standard negative-binomial frameworks is striking. It may indicate sensitivity to dispersion estimation, normalization, filtering, contrast construction, outlier handling, or the multiple-testing family. It cannot be treated merely as one bar in a robustness figure.

Please provide:

- The complete edgeR model specification, design matrix, contrast, TMM normalization settings, dispersion-estimation choices, robust estimation settings, and quasi-likelihood parameters.
- Whether edgeR-adjusted P values were calculated across all expressed genes or only across the 206 DESeq2-selected candidates. They must be genome-wide if this is intended as an independent inferential framework.
- A DESeq2-versus-edgeR effect-size scatterplot for all tested genes and for the 206 candidates.
- Concordance of standard errors, dispersions, nominal P values, and adjusted P values.
- Raw or normalized count plots for the 16 internally robust genes, the two externally supported genes, and representative DESeq2-only genes.
- An explanation of which internal gate each of the two externally supported genes failed.
- Sensitivity to DESeq2 Cook’s-distance handling, independent filtering, and alternative size-factor estimation.
- A check that the same coefficient and sign convention were used in both packages.

The current results suggest that “206 discoveries” is too strong. A more defensible hierarchy would be:

- 262 DESeq2 statistical candidates;
- 206 candidates retained after technical QC;
- 19 cross-method significant candidates;
- 16 candidates passing the complete registered robustness procedure.

### 5. The statistical treatment of effect thresholds and post-selection QC needs justification

The discovery rule combines a BH-adjusted test of a zero interaction effect with a post hoc requirement that the observed absolute log2 fold change exceed log2(1.5). If the intended claim is that effects exceed a biologically meaningful minimum, a test of the composite null \(|\beta| \leq \log_2(1.5)\), such as an effect-thresholded test, is statistically more appropriate than testing \(\beta=0\) and then filtering by the observed effect.

Similarly, the 31 mappability failures and 25 gene-model failures appear to have been removed after the 262 statistically significant genes were selected. The manuscript should either:

- apply the predeclared mappability and gene-model eligibility criteria to all genes before testing and recompute BH-adjusted P values over the eligible universe; or
- provide a formal justification for why the post-rejection filtering preserves the stated error-control interpretation.

Please also specify:

- the precise mappability threshold;
- the precise definition of “gene-model ambiguity”;
- whether these metrics were computed for all 19,445 genes before inference;
- the number of genes removed from the complete testing universe under each filter;
- whether the main conclusions change when QC is applied before statistical testing.

The exact criteria used in the leave-one-library-out and observed-mapping gates should also appear in the main Methods, rather than being summarized only as “direction-agreement, effect-difference, and q-value criteria.”

### 6. Biological-replicate independence, batch structure, and statistical power remain fundamental limitations

The manuscript states that source-tree, pooling, harvest, and extraction independence cannot be established for the discovery libraries, and therefore all inference is conditional on deposited-library independence. This is an important caveat, but it is sufficiently consequential that more should be done than acknowledging it in the Discussion.

Please provide a sample-provenance table for every cohort containing, where available:

- SRA run and BioSample identifiers;
- source plant or tree;
- biological material and pooling information;
- harvest and extraction batch;
- sequencing run, lane, library preparation, and strandedness;
- treatment, cultivar, tissue, and time;
- whether the three libraries are demonstrably independent biological replicates.

The independence audit should cover the external datasets as well as discovery. External “support” is not independent biological validation if the deposited libraries are technical replicates or pooled aliquots.

Given three libraries per design cell, the manuscript should also include an empirical or simulation-based power analysis for interaction effects. The many unsupported external results may reflect limited power, context dependence, or absence of an effect; the current analysis cannot separate these possibilities. Confidence-interval distributions and minimum detectable effects would help prevent binary thresholding from dominating the interpretation.

Potential batch confounding should also be examined. The PCA shows strong cultivar separation, but the axes lack variance-explained percentages and the manuscript does not show whether cultivar, treatment, and sequencing batch are confounded.

### 7. Mappability QC does not fully address cultivar-specific reference bias or infection-associated compositional effects

All cohorts are quantified against a single lychee reference assembly. The authors appropriately acknowledge residual reference bias, but exon uniqueness and ambiguous-read filtering primarily address multi-mapping; they do not necessarily address allele-dependent alignment bias among cultivars.

This matters particularly in a cultivar-interaction study. Please consider at least one of the following sensitivity analyses:

- mask known polymorphic positions;
- construct cultivar-aware pseudoreferences where genotype information is available;
- use a variant-aware or WASP-like remapping strategy;
- restrict analysis to highly conserved regions;
- quantify the association between estimated effects and cultivar-specific mismatch rates.

The joint host–pathogen reference is a sensible choice, but additional details are needed. Please report:

- the pathogen reference accession and annotation version;
- host and pathogen mapping fractions for each library;
- whether size factors were estimated from host genes only;
- sensitivity to large variation in pathogen RNA burden;
- whether pathogen fraction correlates with the leading PCs or candidate-gene effects.

A differing pathogen fraction may represent real disease progression, but it may also induce compositional changes in host RNA-seq libraries that affect normalization.

### 8. The external evaluation is informative, but several interpretations are statistically or biologically too strong

#### Cultivar comparability

The discovery contrast is Yurong1 response minus Guiwei response, while the external contrast is Heiye response minus Guiwei response, with Heiye described as resistant and Guiwei as susceptible. The main text does not clearly establish whether Yurong1 has a resistance phenotype comparable to Heiye relative to Guiwei.

Because external support requires directional agreement, the biological meaning of the sign depends on this relationship. Please provide a cultivar-phenotype table with evidence for relative susceptibility, disease severity, developmental stage, and inoculation protocol. If Yurong1 and Heiye cannot be placed on a comparable resistance axis, the external analysis should be framed as cross-cultivar response transport rather than resistance validation.

#### Zero overlap does not establish independence

The manuscript states that internal stability and cross-context transport were “empirically independent” because the 16 internally robust genes and two externally supported genes did not overlap.

Given 16 and 2 selected genes among 206, independence predicts an expected overlap of only:

\[
16 \times 2 / 206 \approx 0.155.
\]

Under a hypergeometric model, the probability of observing zero overlap is approximately 0.85. Thus, zero overlap is entirely expected under independence and provides almost no empirical evidence about association between the two properties.

Please replace “empirically independent” with the descriptive statement that the thresholded sets did not overlap. A Fisher exact or hypergeometric analysis with an uncertainty interval should be reported. More informative analyses would include:

- correlation of continuous discovery and external effects;
- sign concordance;
- regression accounting for uncertainty in both estimates;
- external-effect distributions among internally robust versus other candidates.

#### “Retirement” is too strong for cross-context contradictions

The manuscript appropriately notes that tissue, comparator, and time differences make external non-support biologically ambiguous. Yet five opposite-direction genes are “retired” under the tier system. An opposite response in pericarp/Heiye may reflect true context specificity rather than invalidating the original leaf/Yurong1 interaction.

“Retired” is reasonable for mapping failure or irreconcilable annotation error. For external direction reversal, a more precise label would be:

> Internally discovered but contradicted for cross-context directional transport.

The tier system should preserve the distinction between validity in the discovery context and portability to a different biological context.

### 9. The promoter analysis does not demonstrate that background choice caused the exploratory enrichment

The exploratory analysis used:

- 18 selected genes;
- PlantCARE exact elements;
- 2-kb promoters;
- randomized GC-matched sequences.

The confirmatory analysis used:

- apparently a different foreground, although the precise foreground must be clarified;
- 927 JASPAR position-weight matrices;
- 1-kb and 2-kb windows;
- expression- and GC-matched genomic backgrounds;
- AME and FIMO;
- a stringent 80-of-100-background robustness rule.

Because the foreground genes, motif definitions, scoring procedures, and robustness criteria all changed, the analysis cannot isolate background choice as the reason the exploratory signal disappeared. The Discussion statement that “background choice, not biology, produced the exploratory enrichment signal” is therefore not demonstrated.

The authors should either:

1. repeat the same PlantCARE motif analysis on the same 18 promoters while changing only the background construction; or
2. analyze the same foreground and same JASPAR matrices against both randomized and matched genomic backgrounds; or
3. substantially temper the conclusion to state that the original motif findings were not robust to a more stringent but methodologically different analysis.

Please also define the foreground used in the registered motif analysis and report the power or calibration of the 80/100 threshold. A procedure may be preregistered yet still be so stringent that meaningful enrichment is nearly impossible to detect.

### 10. Annotation and tier construction require clarification

The Results state that InterPro domain architectures were unavailable for all 206 candidates, contributing to zero high-confidence annotations. However, the Methods state that targeted InterPro/Pfam assignments formed one of three annotation classes. These statements appear inconsistent.

Please clarify:

- whether InterProScan was actually run on the 206 protein sequences;
- what “precomputed InterPro architecture” means;
- what information was available from Pfam;
- how “supported coverage” was calculated;
- what constitutes an architecture conflict;
- why Swiss-Prot plus one-to-one Oryza orthology could not satisfy the two-class rule;
- the difference between an “unannotated” gene and an “annotation failure” that triggers retirement.

The feasibility of Tier A also needs discussion. If the small-RNA class is structurally untestable, no motif is allowed to count, literature using the accessions is excluded as independent support, and no gene can satisfy the annotation gate, then Tier A may be impossible by construction rather than simply empty because the data were unconvincing.

A multidimensional evidence matrix may be more informative than reducing all results to a single ordinal tier. At minimum, the manuscript should distinguish:

- unavailable evidence;
- tested but negative evidence;
- ambiguous evidence;
- contradictory evidence;
- technical failure.

Table 3’s term “Partial” also needs a deterministic definition and should be replaced or supplemented with the actual external effect, confidence interval, adjusted P value, and failed criterion.

### 11. Pathway, signature, and transcript-usage analyses are not sufficiently reproducible from the main text

The manuscript presents substantial pathway, signed-signature, and differential-transcript-usage results, but several essential details are missing.

For pathway analysis, please report:

- the total number of Plant Reactome pathways tested;
- stable pathway identifiers, not only shortened names such as “maturation”;
- the original and mapped gene-set sizes;
- one-to-one orthology coverage;
- the background gene universe;
- the primary test used to generate the reported q values;
- how camera, roast, fgsea, leading-edge deletion, and matched nulls were combined;
- why passing both competitive and self-contained null hypotheses is biologically required.

For the signed 206-gene score, provide an explicit equation and explain:

- the expression transformation;
- whether genes were centered or standardized within a cohort;
- how apeglm weights were normalized;
- how missing genes were handled;
- whether scoring used sample-level expression or modeled contrast estimates;
- the statistical model used for score testing;
- the exact multiple-testing family.

Without this information, the sign reversals across tissues and times are difficult to interpret or reproduce.

For differential transcript usage, please define:

- what constitutes one of the 225 “events”;
- the transcript- and gene-level thresholds;
- the interaction parameter tested by DRIMSeq and DEXSeq;
- how the two packages were combined;
- the stageR screening and confirmation families;
- any minimum change in transcript usage;
- why all 225 events became untestable in PRJNA922966 because of “annotation incompatibility,” particularly if the same reference annotation was used.

The relevant methods currently summarize several complex analyses in only a few sentences.

### 12. The biological interpretation should be moderated

The manuscript repeatedly describes the 12 Tier B genes as “enriched” for carbohydrate, cell-wall, lipid-transfer, chaperone, and RNA-metabolism functions. However, I could not find a formal functional-overrepresentation test for this 12-gene set. The Results describe a qualitative clustering of annotations rather than statistical enrichment.

Unless a formal test is added using an appropriate annotated background, “enriched for” should be replaced with language such as:

> The Tier B set includes several genes annotated with functions related to carbohydrate and cell-wall metabolism.

This is especially important because:

- the set contains only 12 genes;
- several annotations are family-level or provisional;
- no gene is both internally robust and externally supported;
- the cell-wall theme is assembled from different genes at different evidence levels;
- the externally supported genes themselves failed the internal robustness procedure.

The sentence “The biology that does survive scrutiny coheres around a recognizable theme” should therefore be softened. The data generate a plausible cell-wall and carbohydrate-metabolism hypothesis, but they do not yet demonstrate a coherent resistance mechanism.

For a computational genomics or data-resource journal, experimental validation may reasonably be presented as future work. For a journal emphasizing biological mechanism, independent qPCR and preferably functional testing would be necessary before the candidates can support a substantial biological conclusion.

### 13. Code, protocol, and supplementary resources must be permanently accessible

The manuscript states that the protocol, amendment log, complete result tables, workflow, environment, fixtures, and checksums accompany “this repository,” but the attached version does not provide a persistent repository identifier or direct archival citation. The supplementary materials are described but were not included with the manuscript I reviewed.

Before publication, the authors should provide:

- a permanent Zenodo, OSF, or equivalent DOI;
- an immutable release matching the submitted manuscript;
- the preregistration and every amendment;
- exact software versions and container or lock files;
- raw-accession manifests and checksums;
- code from raw FASTQ retrieval through every final table and figure;
- random seeds and generated background sets;
- source tables for all figures;
- a clear software and data license;
- a small test workflow that can be executed independently.

Until these materials are available, the manuscript’s strongest methodological claim—reproducible, prospectively controlled analysis—cannot be independently assessed.

## Minor comments

1. **Figure 1C:** Add percentage variance explained to PC1 and PC2, label individual samples or SRA runs, and indicate any known sequencing or extraction batches.

2. **Figure 2A:** State whether plotted interaction effects are unshrunken or shrunken. Report separately how many genes pass q < 0.05 alone, the effect-size criterion alone, and both.

3. **Figure 3C:** Report Pearson and Spearman correlations with confidence intervals, as well as sign-concordance statistics. The identity line may imply that equal effects are expected despite the deliberate biological differences between cohorts.

4. **External candidates:** Add a table containing the two supported genes and five contradictory genes, with discovery and external effects, standard errors, confidence intervals, q values, abundance, mapping status, and failed robustness gates.

5. **Table 3:** Replace the qualitative external label “Partial” with the numeric external result and the exact criterion that was not met.

6. **Gene-expression visualization:** Include replicate-level normalized-count plots for the 12 Tier B genes and the two externally supported genes. This is particularly important with three libraries per cell.

7. **Pathway reporting:** Give Plant Reactome identifiers, mapped set sizes, and leading-edge genes. “Maturation” is too nonspecific to interpret without an identifier.

8. **Figure 5:** The figure combines DTU, annotation, external follow-up, motif analysis, small-RNA eligibility, and tiers. It is visually dense and would be clearer as two figures or with some panels moved to the supplement.

9. **PRJNA1090613:** Because its time and resistance metadata could not be resolved, consider moving its result from the principal signature figure to a supplementary exploratory panel.

10. **Time-course model:** Explicitly state that time was modeled as a categorical factor and provide the contrast vectors used to estimate the 6-, 24-, and 48-hour cultivar-by-infection effects.

11. **Tool versions and parameters:** Add versions and essential parameters for the confirmatory STAR, featureCounts, Salmon, DESeq2, edgeR, GenMap, DIAMOND, DRIMSeq, DEXSeq, stageR, AME, and FIMO analyses.

12. **Terminology:** Standardize “lychee” versus “litchi” in the prose and explain the relationship between historical *Phytophthora litchii* terminology and *Peronophythora litchii* where relevant.

13. **Biological citations:** Add primary references for claims about apoplastic sugar status, cell-wall remodeling in oomycete resistance, DIR1-mediated systemic acquired resistance, and jasmonate–salicylate antagonism.

14. **Statistical language:** Use “unsupported at the prespecified thresholds” consistently. Avoid allowing “unsupported” to be interpreted as evidence of no biological effect.

15. **Standard declarations:** Add funding, conflicts of interest, author contributions, and data/code licensing statements as required by the target journal.

## Suggested editorial decision

**Major revision.** The manuscript has a strong and potentially publishable methodological core, especially its transparent reporting of null and contradictory findings. Acceptance should depend on clarifying the preregistration chronology, reframing the external analysis as cross-context evaluation, separating the original infection-response claims from the interaction audit, resolving the DESeq2–edgeR discrepancy, strengthening the statistical treatment of QC and effect thresholds, and correcting the overinterpretation of the zero-overlap, motif, and tier results. In its present form, the manuscript supports a carefully qualified computational resource and methodological case study, but not a genome-wide validation of biologically portable resistance markers.
