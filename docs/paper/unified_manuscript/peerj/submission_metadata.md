# PeerJ submission metadata

## Journal and article type

- Journal: PeerJ — the Journal of Life & Environmental Sciences
- Article type: Research Article
- Recommended section: Bioinformatics and Genomics

### Why Research Article is the correct type

The manuscript asks a biological question, analyzes RNA-sequencing data to test that question, reports original statistical results, and reaches biological conclusions. The fact that the underlying reads were already public does not turn the study into a review or data report.

- Not a systematic review/meta-analysis: the study does not synthesize effect estimates from a protocol-driven search of publications, and it has no PRISMA flow diagram or checklist.
- Not a Method Paper: the main contribution is not a new or substantially improved method validated against alternatives. The registered workflow is the means of answering the biological question.
- Not a Data Report: the paper tests hypotheses and reaches conclusions rather than primarily describing a newly curated reusable dataset. PeerJ explicitly directs such studies to Research Article.
- Not a Registered Report: the manuscript already contains results, and its protocol did not receive PeerJ Stage 1 in-principle acceptance. “Preregistered analysis” in the title describes the study design; it is not the submission type.

## Title

Cultivar-dependent transcriptional responses of lychee to *Peronophythora litchii*: a registered genome-wide analysis

## Short title

Cultivar-dependent lychee responses to *P. litchii*

## Structured abstract

**Background.** Litchi downy blight, caused by the oomycete *Peronophythora litchii*, is among the most damaging diseases of lychee (*Litchi chinensis* Sonn.). Public RNA-sequencing cohorts spanning cultivars, tissues, and infection time points offer a resource for identifying cultivar-dependent infection responses, but they are easily over-interpreted when the same cohort is used both to select candidates and to appear to confirm them.

**Methods.** We unified an exploratory reanalysis with a prospectively registered confirmatory stage. The confirmatory protocol fixed dataset roles, statistical models, thresholds, and evidence vocabulary before external outcomes were examined. It combined a genome-wide negative-binomial cultivar-by-infection analysis with mapping and gene-model quality control, independent statistical and quantification checks, prespecified evaluation in independent public cohorts, and deterministic evidence integration.

**Results.** Among 19,445 expressed genes, 262 met the genome-wide interaction threshold; 206 passed mapping and gene-model quality control, 19 remained significant under an independent edgeR quasi-likelihood analysis, and 16 passed the complete registered robustness procedure. In a prespecified cross-context evaluation against an independent pericarp time course, two genes were supported and five were directionally contradictory. The internally robust and externally supported sets did not overlap, an outcome compatible with chance given the set sizes. None of 18 exploratory candidates met the subsequent genome-wide interaction criterion, and two failed uniform-mappability control. Evidence integration assigned no gene to the highest confidence tier, placed 12 internally robust genes in a middle tier, and retired 65 entities.

**Conclusions.** Candidates selected for effect-size prominence in one cohort largely failed a formally specified genome-wide interaction test. The analysis defines the claims supported by the available public data and releases a reproducible candidate resource with explicit evidence boundaries. Experimental perturbation remains necessary for causal conclusions.

## Keywords

1. *Litchi chinensis*
2. *Peronophythora litchii*
3. plant-pathogen interaction
4. RNA sequencing
5. cultivar-dependent response
6. preregistered analysis

## Subject areas

Recommended selections, in priority order:

1. Plant Science
2. Genomics
3. Bioinformatics
4. Agricultural Science
5. Molecular Biology

## Author and submission administrator

- First name: Eric
- Last name: Zhuang
- Affiliation: NYU Langone Health
- Correspondence street address and ZIP/postal code: **[AUTHOR INPUT REQUIRED]**
- City: New York
- State: New York
- Country: USA
- Email: eric.zhuang@nyulangone.org
- ORCID iD: 0009-0001-9050-0214
- Corresponding author: Yes
- Submission administrator: Eric Zhuang

## Author contributions

Eric Zhuang: conceptualization, data curation, formal analysis, investigation, methodology, project administration, software, validation, visualization, writing—original draft, and writing—review and editing. The author approved the submitted version and is accountable for the work.

## Funding

This work received no external funding.

## Competing interests

The author declares no conflicts of interest.

## Ethics

This study reanalyzed publicly available sequencing datasets and involved no new experiments with humans, human tissue, animals, or field sampling; ethical approval was not required.

## Data availability

All analyzed sequencing data are public under PRJNA830488/GSE201243, PRJNA450886, PRJNA922966/GSE222651, PRJNA922965/GSE222650, and PRJNA1090613/GSE262200. Supplementary Tables S1–S18, Figures S1–S3, and tab-separated figure source data are archived under CC BY 4.0 at <https://zenodo.org/records/22436625>. The supplementary tables, figures, and source data, together with the exact analysis code, Snakemake workflows, scripts, configurations, tests, metadata, and environment specifications used for this study, are supplied as `PeerJ_supplemental_data_S1.zip`.

### Current DOI update required — do not paste this note

Before submission, publish the exact PeerJ supplement as a new Zenodo version and replace the DOI above with that new version-specific DOI. The currently cited September 1 version has the data, figures, and figure source data but no analysis-code directory and does not exactly match the PeerJ supplement.

## Generative-AI disclosure

OpenAI Codex (GPT-5; accessed September 6, 2026) was used to assist with language editing and journal-specific document formatting. It was not used to generate data, perform analyses, interpret results, or draw scientific conclusions. The author confirms that the originality and accuracy of the content were checked, that the applicable OpenAI terms of use were reviewed and judged suitable for publication, and that full responsibility is accepted for the integrity of the manuscript, including the accuracy of its references. The pre-edit and edited versions have been retained and can be supplied to the Editor on request.

The author must verify every clause of this statement before submission and update the model label if the Codex interface exposes a more specific version.

## Confidential note to staff about secondary-data scope

This Research Article reanalyzes five public RNA-sequencing cohorts to answer a cultivar-by-infection biological question not tested in the original publications. The study prospectively assigned cohorts to discovery, primary external evaluation, generic transfer, orthogonal modality, and exploratory roles; used independent statistical and quantification checks; and reports supported, null, and contradictory results. No new wet-lab or clinical data were generated. The manuscript and Supplemental Data S1 provide complete data provenance, code, workflows, frozen results, and reproducibility materials.

## Submission declarations

- The manuscript is not under consideration by another journal and has not been published as a peer-reviewed article.
- The sole author approved the submitted version and accepts responsibility for the integrity of the work.
- All figures and tables were generated for this study and contain no third-party copyrighted material.
- The study involved no human participants, identifiable human material, vertebrate animals, or new field sampling.
- The full peer-review history may be published under PeerJ's current open peer-review policy.

## Main-figure titles and legends

### Figure 1

**Title:** Study cohorts, discovery quality control, and expression structure.

**Legend:** (A) The five public cohorts with prespecified roles and deposited library counts. (B) Per-library technical quality in the discovery cohort: fastp read survival, STAR unique-alignment rate, and Salmon mapping rate; all 12 libraries passed the fixed inclusion gates. (C) Principal-component analysis of the discovery libraries separates cultivar and infection status.

### Figure 2

**Title:** Genome-wide discovery and formal reassessment of the exploratory candidates.

**Legend:** (A) Cultivar-by-infection interaction effects across 19,445 expressed genes; 262 genes met the statistical threshold and 206 were retained after uniform mapping and gene-model quality control. (B) Genome-wide re-estimation of the 18 exploratory (legacy) candidates with 95% confidence intervals; orange marks uniform-mappability failures. No legacy candidate met the genome-wide interaction criterion. (C) Evidence attrition from tested genes to internally robust candidates.

### Figure 3

**Title:** Internal robustness and the primary external evaluation.

**Legend:** (A) Candidates passing each predeclared robustness gate, the conjunction of the four analytic gates, and the additional observed-mapping gate. (B) The internally robust set (16 genes) and the externally supported set (2 genes) do not overlap. (C) Discovery interaction effects against the primary cross-context interaction effects (Heiye response minus Guiwei response, pericarp, 24 h); supported, contradictory, and internally robust genes are highlighted. The diagonal is a visual reference only; equal effects across contexts are not expected.

### Figure 4

**Title:** Frozen pathway and signature evaluation.

**Legend:** (A) Discovery normalized enrichment scores for the six frozen pathways; only circadian rhythm passed all internal gates, and none was supported in the primary external evaluation. (B) The frozen signed 206-gene signature across the six non-exploratory external contrasts; filled points denote *q* < 0.05. The quarantined PRJNA1090613 estimate is in Figure S3.

### Figure 5

**Title:** Conditional transcript usage.

**Legend:** (A) Discovery gate and event counts. (B) External follow-up of the 225 discovery events, separated by prespecified study role.

### Figure 6

**Title:** Orthogonal evidence and final tiers.

**Legend:** (A) Annotation status of the 206 quality-control-retained genes. (B) Registered promoter-motif robustness and the small-RNA reference gate. (C) Deterministic final tiers over all 268 frozen entities.

## Main-table titles

- Table 1. Locked dataset roles and eligibility.
- Table 2. Formal genome-wide audit of the 18 exploratory-stage candidates.
- Table 3. Cross-context supported and contradictory genes in the primary external evaluation (PRJNA450886, pericarp, 24 h).
- Table 4. The twelve Tier B genes: internally robust genome-wide statistical candidates with direction-consistent but sub-threshold, or non-measurable, primary external evidence.

## Editor and reviewer suggestions

Do not enter names until the author has checked each person's expertise, present institution, recent collaborations, co-authorship, personal relationships, and other conflicts. Suitable expertise includes plant-pathogen transcriptomics, plant genomics, RNA-sequencing interaction models, and reproducible bioinformatics.
