# Abstract

Litchi downy blight, caused by the oomycete *Peronophythora litchii*, severely damages lychee (*Litchi chinensis* Sonn.). Public RNA-sequencing cohorts spanning cultivars, tissues and infection times provide an opportunity to identify reproducible host responses and prioritize resistance candidates. We integrated five such cohorts in a two-stage analysis of the lychee–*P. litchii* interaction. An exploratory reanalysis of Guiwei and Yurong1 leaves identified 17 and 117 infection-responsive genes, respectively, and nominated 18 defense-associated candidates. We then prospectively registered genome-wide discovery and cross-context evaluation. Cultivar-by-infection analysis of 19,445 expressed genes identified 262 statistical candidates; 206 passed uniform mapping and gene-model quality control, 19 were significant under both DESeq2 and edgeR genome-wide analyses, and 16 passed the complete registered robustness procedure. Evidence integration prioritized 12 internally robust genes spanning carbohydrate and cell-wall remodeling, membrane and lipid transport, chaperone regulation, RNA metabolism and specialized metabolism. In an independent pericarp time course contrasting susceptible and resistant cultivars, alpha-xylosidase LITCHI005518 and LITCHI001963 showed cross-context support. A 206-gene signature distinguished infection responses across tissues, with a significant leaf–fruit interaction demonstrating tissue and temporal dependence. Estimand-aligned follow-up confirmed infection responsiveness for 13 of 18 exploratory candidates in Guiwei and 16 of 18 in Yurong1, while the genome-wide interaction analysis refined their interpretation as within-cultivar rather than cultivar-differential responses. This analysis provides a prioritized candidate set and defines contexts for experimental evaluation.

**Keywords:** downy blight; disease resistance; RNA sequencing; cultivar-by-infection interaction; transcript usage; reproducible bioinformatics

# Why this research matters

Downy blight damages lychee leaves, flowers and fruit, but few molecular candidates have been prioritized consistently across available studies. We reanalyzed five public sequencing datasets using a prospectively registered workflow that separated gene discovery from evaluation in different cultivars, tissues and infection times. The analysis identifies a stable group of candidate genes, highlights cell-wall and carbohydrate processes, and shows that many infection responses depend on biological context. All data, code and detailed results are public. The findings provide a transparent shortlist for laboratory validation and illustrate how existing plant datasets can be combined without overstating what computational evidence alone can establish.

# 1 Introduction

Lychee (*Litchi chinensis* Sonn.) is an economically important subtropical fruit crop. Litchi downy blight, caused by the oomycete *Peronophythora litchii*, affects young leaves, inflorescences and fruit and contributes to postharvest decay (Sun et al., 2017; Yi et al., 2010). Molecular studies have implicated cultivar-specific early responses, calcium-dependent signaling and pathogen manipulation of host ethylene biosynthesis (Sun et al., 2019; Liu et al., 2023; Li et al., 2023). These results provide plausible resistance mechanisms, but candidate selection across the available transcriptomes has not been evaluated under a common genome-wide framework.

The availability of a chromosome-scale, haplotype-resolved lychee genome now supports locus-level transcriptomic analysis in this highly heterozygous crop (Hu et al., 2022). At the same time, reliance on a single reference creates a potential asymmetry when cultivars differ from the reference haplotypes. Candidate evaluation should therefore consider exon uniqueness, gene-model ambiguity and sensitivity to mapped reads alongside statistical significance. These controls are particularly important for resistance research, where apparent cultivar differences can arise from biological regulation, sampling variation or reference-dependent quantification.

The necessary datasets now span cultivars, leaf and pericarp tissues, messenger and small RNA, and several infection times. Their reuse can address a biological question distinct from the individual source studies: which host responses are stable under analytical perturbation, and which transport across tissue and cultivar contexts? This distinction matters because differential expression within one cultivar is not equivalent to a cultivar-by-infection interaction, and interaction effects are difficult to estimate with the three deposited libraries typically available per experimental cell.

The available cohorts are complementary rather than exchangeable. The strongest independent candidate-evaluation cohort differs from discovery in tissue, resistant comparator and temporal design; another cohort compares infection responses between leaf and fruit without a cultivar contrast. Consequently, agreement across studies is evidence of transport across biological contexts, not direct replication of the same estimand. Conversely, a response reversal can expose tissue- or genotype-dependent regulation rather than invalidate the original discovery. We use “cross-context support” to preserve that distinction.

The central analytical challenge is to match the statistical estimand to cultivar dependence. A gene may respond strongly to infection in one or both cultivars without showing a precisely estimated difference between their responses. Selecting genes from within-cultivar contrasts and then comparing their observed fold changes can therefore favor extreme, imprecise estimates. A genome-wide interaction model instead tests the response difference directly and defines the multiplicity family before candidates are selected. Independent quantification, an alternative count model, mapping checks and cross-context evaluation can then distinguish statistical discovery from analytical stability and transportability.

This project began with an exploratory reanalysis of the GSE201243 leaf series. That stage identified infection-responsive genes within Guiwei and Yurong1 and nominated 18 defense-associated candidates, including lectin, pathogenesis-related, heat-shock, lipid-transfer and calcium-binding proteins. It also generated promoter-motif hypotheses. Those findings motivated, but did not determine, the registered genome-wide analysis. The present study retains the exploratory results as a distinct evidence layer and reevaluates them using models aligned with both within-cultivar responsiveness and cultivar-by-infection interaction.

We therefore distinguish three questions. Statistical discovery asks which genome-wide interaction effects cross the prespecified significance and magnitude thresholds. Internal robustness asks whether those effects survive changes in quantification, statistical framework, expression filtering, individual libraries and mapping assumptions. Cross-context evaluation asks which frozen signals remain detectable in independent public cohorts. Functional annotation, promoter motifs and small RNA are treated as separate evidence classes because biological plausibility cannot substitute for expression support.

We combined an exploratory analysis with a prospectively registered confirmatory workflow. The latter fixed dataset roles, models, thresholds and evidence terminology before external outcomes were processed. We used genome-wide interaction testing, independent quantification, an alternative statistical framework, leave-one-library-out refitting, mapping controls, pathway and transcript-usage analyses, and frozen evaluation in independent cohorts. Our objectives were to identify robust cultivar-dependent responses, evaluate their context dependence, and produce a prioritized and openly reproducible resource for experimental follow-up.

# 2 Materials and Methods

## 2.1 Study design and datasets

The exploratory stage analyzed the Guiwei and Yurong1 leaf series GSE201243/PRJNA830488 at 24 h after inoculation. The confirmatory protocol was time-stamped before confirmatory expression outcomes were generated and assigned five public cohorts to fixed roles. PRJNA830488 was the sole discovery cohort; PRJNA450886 was the primary cross-context evaluation, comparing Guiwei and Heiye pericarp at 6, 24 and 48 h; PRJNA922966 tested generic transfer between leaf and fruit; PRJNA922965 supplied an orthogonal small-RNA modality; and PRJNA1090613 remained exploratory because its time and resistance metadata could not be standardized (NCBI, 2026a–e). The protocol, amendment chronology, complete outputs and environments are archived on Zenodo (Zhuang, 2026). Detailed methods and locked dataset roles are provided in Supporting Information Methods S1 and Table S19.

Protocol version 1.0.0 fixed the dataset roles, biological-unit rules, primary coefficients, significance and effect thresholds, conditional gates, external-unlock procedure and evidence terminology. Outcome-blind implementation clarifications were recorded in an amendment log rather than silently incorporated. Because all cohorts were already public, the staged unlock was a workflow-enforced computational safeguard rather than experimental blinding. Source-tree, pooling, harvest and extraction independence were not consistently reported, so inference is conditional on the deposited libraries being independent biological units.

## 2.2 Processing, discovery and robustness

Reads were trimmed and aligned to a joint host–pathogen reference based on the lychee genome assembly of Hu et al. (2022), and host genes were counted with featureCounts; Salmon provided independent transcript quantification (Chen et al., 2018; Dobin et al., 2013; Liao et al., 2014; Patro et al., 2017). Libraries required at least 10 million surviving read pairs and at least 40% uniquely aligned reads. DESeq2 fitted the design `cultivar + treatment + cultivar:treatment` with Guiwei and mock as reference levels (Love et al., 2014). Genes required counts of at least 10 in at least three libraries. Statistical candidates required genome-wide Benjamini–Hochberg-adjusted *q*<0.05 and absolute interaction log2 fold change ≥log2(1.5) (Benjamini and Hochberg, 1995). Uniform exon mappability and gene-model checks were applied to every tested gene (Pockrandt et al., 2020).

Frozen candidates were assessed by Salmon-based gene quantification, edgeR quasi-likelihood testing, a counts-per-million filter and all 12 leave-one-library-out refits (Robinson et al., 2010). Observed read-mapping sensitivity formed an additional gate. Pathways were transported through one-to-one rice orthology and assessed by complementary competitive, rotation and enrichment procedures (Naithani et al., 2024; Wu and Smyth, 2012; Wu et al., 2010). Differential transcript usage used a stage-wise gene and transcript error-control procedure (Nowicka and Robinson, 2016; Van den Berge et al., 2017). Snakemake workflows enforced the registered stage boundaries and generated manifests (Mölder et al., 2021).

The Salmon gate required agreement in direction and an absolute effect difference no greater than 0.5 log2 units. The edgeR gate used the identical design matrix and coefficient, genome-wide adjustment and a prespecified *q*<0.10 threshold with direction agreement. The leave-one-library-out analysis required direction agreement in all 12 refits and *q*<0.10 in at least 10. These gates were combined conjunctively; they were not an additive score. The pathway workflow additionally tested sensitivity to leading-edge removal and expression- and length-matched null sets. Transcript-usage testing proceeded only if its registered stage-wise error-control gate was satisfied.

## 2.3 Cross-context evaluation and evidence integration

The primary external estimand was the Heiye-minus-Guiwei difference in infection response at 24 h in PRJNA450886. Candidate tests were adjusted across the frozen candidate-by-contrast family and required *q*<0.05, absolute log2 fold change ≥log2(1.5), a 95% confidence interval excluding zero and agreement with the discovery direction. Significant opposite-direction effects were recorded as response reversals. A signed 206-gene score evaluated broader transfer across tissue and time.

The external model used cultivar, treatment, categorical time and their interactions, with 24 h as the reference time. The 6- and 48-h contrasts were secondary. PRJNA922966 used a tissue-by-treatment model to test generic transfer because it could not estimate cultivar dependence. Frozen signature weights were derived only from discovery and were not updated after external outcomes were available. Thus, candidate, pathway and signature evaluations addressed complementary levels of transport without allowing an external result to change discovery membership.

Functional labels combined curated protein matches, domains and one-to-one rice orthology. Promoter motifs were tested against expression- and GC-matched genomic backgrounds, and the small-RNA reference was audited before use. Prespecified evidence tiers combined discovery, robustness, cross-context, mapping and annotation evidence without additive scoring. Negative-binomial simulations estimated conditional detection probability under the deposited three-library-per-cell designs. Supporting Information Methods S1 gives all software versions, thresholds, sensitivity analyses and empty-result rules.

Tier A required complete internal robustness, primary cross-context support, clean mapping and annotation, and attributable orthogonal evidence. Tier B retained internally robust candidates when external or orthogonal evidence was partial or not testable, while Tier C was reserved for a robust and externally supported pathway. Simulations preserved the observed four-cell designs and fitted mean–dispersion relationships, injected interaction effects over a fixed grid and applied the same multiplicity and effect-size rules as the empirical analyses.

# 3 Results

## 3.1 Study stages and genome-wide discovery

The exploratory within-cultivar contrasts identified 17 infection-responsive genes in Guiwei and 117 in Yurong1 and nominated 18 defense-associated candidates. Promoter screening suggested four enriched motif classes, but these single-cohort results were treated only as hypotheses for the registered analysis. The confirmatory workflow retained all 12 discovery libraries: 99.56%–99.66% of read pairs survived trimming, 84.44%–86.22% aligned uniquely and 80.77%–82.56% mapped with Salmon (Figure 1). Expression structure separated primarily by cultivar and secondarily by infection status.

The exploratory candidates included a jacalin-like lectin, a pathogenesis-related protein, two thaumatin/osmotin-like proteins, a heat-shock protein 70, two lipid-transfer proteins, an EF-hand calcium-binding protein and a phytosulfokine precursor. Screening their 2-kb promoters against randomized GC-matched sequences suggested enrichment of anaerobic-response, methyl-jasmonate-responsive, TCA and TC-rich elements. These candidates and motifs supplied biologically motivated hypotheses, but their selection within one dataset meant that neither the gene list nor its regulatory interpretation could serve as confirmatory evidence without genome-wide reassessment and biologically matched backgrounds.

Principal-component analysis assigned 54.2% of variance to the first component and 16.1% to the second, with no library isolated from its replicate group. The first component primarily separated cultivars, whereas the second captured infection status. These patterns supported joint modeling of cultivar and treatment while also demonstrating why a simple pooled infected-versus-mock contrast would not answer the cultivar-dependent question.

Among 19,445 expressed genes, 262 met the registered genome-wide interaction criterion; 206 remained after uniform mapping and gene-model quality control (Figure 2). Recalculating multiplicity adjustment over only the 13,602 quality-eligible genes recovered all 206 and added 12, showing that the registered filter order was conservative. Nineteen candidates were significant in both DESeq2 and edgeR genome-wide analyses. Eighteen passed all four internal perturbation gates, and 16 remained after observed mapping-sensitivity analysis. Effect estimates agreed closely between DESeq2 and edgeR (*r*=0.995 across all genes and *r*=0.999 across candidates). Circadian rhythm was the only pathway retained across every internal pathway gate.

The individual robustness gates retained 196 candidates under independent quantification, 19 under edgeR genome-wide testing, 205 after the counts-per-million filter and 125 through every leave-one-library-out refit. Their conjunction retained 18 before the mapping-sensitivity step. A stricter post hoc composite-null test, which directly tested whether the interaction exceeded the effect threshold, retained seven of the final 16; an apeglm false-sign-or-small analysis retained 15. These sensitivity results did not redefine the registered candidate set, but they show that most of the final internally robust genes also withstand more demanding effect-size formulations.

Six Plant Reactome pathways met the discovery rule after transport through one-to-one rice orthology: activation and assembly of the pre-replication complex, DNA replication initiation, maturation and circadian rhythm were positively enriched, whereas jasmonic-acid signaling was negatively enriched. Circadian rhythm alone survived the competitive, rotation, leading-edge-deletion and matched-null procedures. The edgeR gate was also deliberately selective: although every candidate had a nominal edgeR *P*<0.05 and all effect directions agreed, only 19 retained genome-wide adjusted support under the registered alternative framework.

Estimand-aligned within-cultivar follow-up confirmed infection responsiveness for 13 of the 18 exploratory genes in Guiwei and 16 in Yurong1. No exploratory gene met the genome-wide interaction criterion; LITCHI001510 reached *q*=0.080, and the EF-hand calcium-binding gene LITCHI019519 had an interaction estimate of −3.33 with *q*=0.106. Thus, the exploratory genes remain supported as within-cultivar infection responses, whereas evidence for cultivar-differential response comes from the genome-wide set (Supporting Information Table S20).

## 3.2 Cross-context responses depend on tissue and time

Of 206 frozen genes, 184 were measurable in the primary external pericarp contrast. Two met all cross-context criteria: LITCHI005518, encoding an alpha-xylosidase associated with xyloglucan remodeling, and the uncharacterized LITCHI001963 (Figure 3; Table 1). Five genes met the magnitude and significance criteria in the opposite direction. Across measurable candidates, discovery and external effects were uncorrelated (*r*=−0.05, 95% CI −0.19 to 0.10), and 51.6% shared direction. The supported and reversed outcomes therefore identify transport and reorganization across tissue and cultivar contexts rather than direct replication of an identical experiment.

LITCHI005518 retained a positive interaction in both studies, with an external effect of 0.67 log2 units and adjusted *q*=0.007; LITCHI001963 retained a negative interaction, with an external effect of −0.94 and *q*=0.007. The five response reversals included genes annotated as caffeoylshikimate esterase, thiamine thiazole synthase, phosphatidylinositol 4-kinase, beta-glucosidase and Fe(II)/2-oxoglutarate-dependent dioxygenase. Reporting these separately from below-threshold outcomes preserves the distinction between loss of detectable evidence and a well-supported change in response direction.

The two externally supported genes did not overlap the 16-gene internally robust set. This does not imply incompatibility between the analyses: with sets of 16 and two drawn from 206 candidates, the expected overlap under independence is 0.16 genes and the probability of zero overlap is 0.85. Internal robustness asks whether discovery survives analytical perturbation in the same leaf cohort, whereas cross-context support asks whether an effect transports to pericarp, another resistant comparator and a different time-course design.

The frozen 206-gene score also varied by context (Figure 4). In the generic-transfer study it tracked infection positively in leaf (0.107, *q*=0.0015) and negatively in fruit (−0.181, *q*<0.001), yielding a leaf–fruit interaction of 0.289 (*q*<0.001). In pericarp, the score was 0.109 at 24 h (95% CI −0.079 to 0.297, *q*=0.349) and −0.240 at 48 h (95% CI −0.428 to −0.052, *q*=0.043). None of the six frozen pathways met the primary external gates.

## 3.3 Transcript usage, orthogonal evidence and prioritized genes

The registered conditional gate for transcript usage was satisfied, identifying 225 cultivar-dependent events across 152 genes. In the primary external cohort, 125 were measurable but below the support thresholds and 100 were not testable; incompatible annotations precluded event-level testing in the generic-transfer cohort (Supporting Information Figure S4).

The transcript-usage events are therefore an internally controlled discovery resource rather than a claim of event-level transfer. They broaden the candidate space beyond total gene abundance and identify genes for which isoform regulation may contribute to cultivar-dependent response. Validation will require compatible transcript annotations or targeted isoform assays, because gene-level mapping alone cannot resolve these events.

Family-level labels were assigned to 150 of the 206 candidates. No candidate met the stricter two-class annotation rule because precomputed domain architectures were unavailable for this non-model crop. No promoter motif passed the family-wise background and sensitivity requirements, and small-RNA coherence was not testable because the frozen reference contained no exact *Litchi* entry. These outcomes were retained as explicit limits rather than replaced with post hoc evidence.

The motif analysis tested 927 plant profiles in both 1-kb and 2-kb promoter windows against 100 expression- and GC-matched backgrounds. The largest background pass count was four, well below the required 80, and no profile passed the independent site-level sensitivity procedure. A controlled follow-up of the exploratory PlantCARE motifs retained several classes against matched genomic promoters, but these remained regulatory hypotheses rather than tier-promoting evidence. The reference audit similarly prevented unrelated small-RNA entries from being treated as species-specific support.

Evidence integration prioritized 12 internally robust Tier B genes (Figure 5; Table 2). They encompass carbohydrate and cell-wall metabolism, sugar and membrane transport, lipid signaling, chaperone regulation, RNA metabolism, chromatin-associated regulation and specialized metabolism. Nine were measurable in the primary external cohort and all nine retained the discovery direction, although their adjusted external tests did not meet every support criterion. Tier A, which additionally required cross-context and attributable orthogonal support, remained empty. Conditional simulations estimated 80% detection at interaction effects of 2.44 log2 units in discovery and 2.11 in external evaluation, emphasizing the limited precision of three-library-per-cell designs.

The Tier B set includes an ERD6-like sugar transporter, a WAT1-related membrane protein, phosphomannomutase/phosphoglucomutase, a serine carboxypeptidase, a chloroplastic starch-branching enzyme, a DIR1-like lipid-transfer protein and a BAG-family chaperone regulator. Exonuclease 1, ribonuclease J and a homeobox-DDT protein add DNA-, RNA- and chromatin-associated functions, while cytochrome P450 81Q32 represents specialized metabolism and one locus remains unannotated. Their retention under every internal gate makes this set a focused starting point for experiments even though the current public cohorts cannot establish molecular function.

At a true interaction effect of 1.5 log2 units, the estimated conditional detection probabilities were 62.7% in discovery and 74.0% in external candidate-family analysis. These simulations condition on the fitted dispersions and deposited design; they do not replace biological replication. They nevertheless provide scale for interpreting adjusted tests and support retaining effect estimates, confidence intervals and evidence labels alongside threshold-based categories.

# 4 Discussion

This analysis identifies a reproducible core of cultivar-dependent transcriptional responses in the lychee–*P. litchii* pathosystem. The evidence hierarchy distinguishes 262 genome-wide statistical candidates, 206 quality-controlled candidates, 19 genes supported by two statistical frameworks, and 16 genes passing the complete internal robustness procedure. It also preserves the separate biological meaning of the exploratory set: most of those genes were reproducibly infection responsive within cultivars, but none had sufficiently precise evidence for a difference between cultivar responses. This distinction prevents a strong within-cultivar response from being misrepresented as cultivar specificity.

The estimand-aligned follow-up is important for interpreting the original 18 genes. Thirteen were significant within Guiwei and 16 within Yurong1, so most remain credible infection-response candidates. Their absence from the genome-wide interaction set instead shows that evidence for responsiveness is not equivalent to evidence that the two cultivars respond differently. LITCHI019519 illustrates the precision issue: its large interaction estimate retained the expected direction, but uncertainty under the small four-cell design prevented genome-wide adjusted support. The registered analysis therefore refines rather than discards the exploratory biology.

The prioritized genes converge qualitatively on cell-wall and carbohydrate dynamics. Tier B includes a phosphomannomutase/phosphoglucomutase, a starch-branching enzyme, an ERD6-like sugar transporter and a serine carboxypeptidase, while the cross-context set contains an alpha-xylosidase acting on xyloglucan. These results are consistent with earlier emphasis on sugar metabolism and wall reinforcement in contrasting lychee cultivars (Sun et al., 2019). A DIR1-like lipid-transfer protein, a BAG-family chaperone regulator and a cytochrome P450 provide additional defense-related candidates; heat-shock regulation has broader links to plant immunity (Berka et al., 2022). These annotations guide experiments but do not establish molecular function.

The convergence suggests several experimentally accessible hypotheses. Cell-wall and carbohydrate candidates could be tested through infection-stage expression profiling coupled to measurements of xyloglucan remodeling, soluble sugars and wall composition. The DIR1-like protein is a candidate for testing systemic or lipid-mediated defense signaling, while the BAG-family regulator provides a link between chaperone activity, stress tolerance and cell-death control. Because the functional labels are family-level assignments, perturbation and biochemical assays should target the lychee loci directly rather than infer function solely from homolog names.

The cross-context alpha-xylosidase strengthens the cell-wall theme because xyloglucan turnover can alter wall accessibility and mechanical properties during infection. In parallel, the ERD6-like transporter, starch-branching enzyme and phosphomannomutase/phosphoglucomutase suggest that carbon allocation may accompany cultivar-dependent defense. The DIR1-like and WAT1-related proteins extend the candidate set to lipid and membrane processes. These signals do not establish a single pathway, but their convergence provides a rational panel for coordinated expression, metabolite and wall-composition measurements during infection.

Cross-context evaluation revealed both transportable signals and biological reorganization. LITCHI005518 and LITCHI001963 passed every criterion across different tissue and cultivar contrasts. Conversely, five response reversals and the opposing leaf and fruit signature estimates demonstrate that direction and magnitude depend on biological context. Internally robust and cross-context-supported sets need not overlap: given sets of 16 and two drawn from 206 genes, the expected overlap under independence is only 0.16. Candidate validation should therefore reproduce the tissue, developmental stage and infection window relevant to its intended use.

The signed 206-gene score complements individual candidates by summarizing coordinated response structure. Its positive association with infection in leaf, negative association in fruit and change across the pericarp time course indicate that the discovery program is reorganized rather than uniformly absent outside the discovery cohort. For crop improvement, this argues against treating a transcriptomic signature as a context-invariant resistance marker. A practical validation design should first reproduce the relevant tissue and infection time, then test transport across a broader panel of susceptible and resistant cultivars.

Beyond the individual candidates, the registered structure provides a reusable approach for secondary analysis of plant transcriptomes. Fixing cohort roles before evaluation limits outcome-driven switching between discovery and validation, while the evidence vocabulary prevents internal robustness from being presented as independent replication. Uniform mapping controls are especially valuable for non-model crops with heterozygous genomes, and explicit empty-result rules allow motif, small-RNA and pathway analyses to stop when their reference requirements are unmet. The resulting evidence table is more useful than a single ranked list because researchers can select candidates according to the tissue, assay and claim they intend to test. Complete source data and executable workflows also make later reanalysis possible when improved lychee annotations and additional infection cohorts become available.

The study remains bounded by public data. Each cultivar–treatment cell contains three deposited libraries, and their source-tree, pooling and extraction independence are not reported; inferential values are conditional on deposited-library independence. Metadata incompletely describe inoculum, leaf development and wounding. All quantification uses one host reference, and no same-tissue, same-time independent replication cohort is available. Mapping analyses address the clearest reference concerns but cannot remove all reference bias. The simulated minimum detectable effects further show that below-threshold external results can reflect limited power as well as biological context. Finally, the candidates have not been experimentally perturbed.

These limitations define tractable next steps: quantitative PCR in independent Guiwei and Yurong1 infections, functional analysis of the alpha-xylosidase and DIR1-like candidates, improved lychee protein-domain and small-RNA references, and promoter-reporter or binding assays for regulatory hypotheses. The public tables and workflows enable those tests to begin from an auditable candidate set rather than a selectively reported list.

# 5 Conclusions

A registered multi-cohort analysis identified 206 quality-controlled interaction candidates, a stable core of 16 genes, 12 internally robust priority genes and two responses supported across an independent tissue and cultivar contrast. The accompanying evidence labels distinguish robustness, context and annotation support for every candidate. This resource provides focused hypotheses for experimental validation and a reusable framework for integrating public plant transcriptomes.

The prioritized loci, complete result tables and executable workflows provide a practical starting point for independent molecular and breeding studies of lychee downy blight.

# Acknowledgements

OpenAI Codex assisted with language editing, manuscript condensation and journal-specific document formatting. It did not generate data or perform analyses. The author verified all scientific statements and accepts responsibility for all content.

# Conflict of Interest

The author declares no conflict of interest.

# Author Contributions

E.Z. conceived and designed the study, curated the data, developed the methodology and software, performed the analyses and validation, prepared all figures and tables, and wrote and revised the manuscript. E.Z. approved the final manuscript and accepts responsibility for all aspects of the work.

# Funding Information

This work received no external funding.

# Data Availability Statement

All analyzed sequencing data are publicly available under PRJNA830488/GSE201243, PRJNA450886, PRJNA922966/GSE222651, PRJNA922965/GSE222650 and PRJNA1090613/GSE262200. Complete result tables, figure source data, the registered protocol and amendment log, analysis code, workflows, tests and environment specifications are archived under CC BY 4.0 at https://zenodo.org/records/22436625.

# Ethics Statement

Not applicable. This study reanalyzed public plant sequencing datasets and involved no new experiments with humans, animals or field sampling.

# References

- Benjamini Y and Hochberg Y (1995) Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society, Series B* 57: 289–300.
- Berka M, Kopecká R, Berková V, Brzobohatý B and Černý M (2022) Regulation of heat shock proteins 70 and their role in plant immunity. *Journal of Experimental Botany* 73: 1894–1909. https://doi.org/10.1093/jxb/erab549
- Chen S, Zhou Y, Chen Y and Gu J (2018) fastp: an ultra-fast all-in-one FASTQ preprocessor. *Bioinformatics* 34: i884–i890. https://doi.org/10.1093/bioinformatics/bty560
- Dobin A, Davis CA, Schlesinger F, Drenkow J, Zaleski C, Jha S et al. (2013) STAR: ultrafast universal RNA-seq aligner. *Bioinformatics* 29: 15–21. https://doi.org/10.1093/bioinformatics/bts635
- Hu G, Feng J, Xiang X, Wang J, Salojärvi J, Liu C et al. (2022) Two divergent haplotypes from a highly heterozygous lychee genome suggest independent domestication events for early and late-maturing cultivars. *Nature Genetics* 54: 73–83. https://doi.org/10.1038/s41588-021-00971-3
- Li P, Li W, Zhou X, Situ J, Xie L, Xi P et al. (2023) *Peronophythora litchii* RXLR effector PlAvh202 destabilizes a host ethylene biosynthesis enzyme. *Plant Physiology* 193: 756–774. https://doi.org/10.1093/plphys/kiad311
- Liao Y, Smyth GK and Shi W (2014) featureCounts: an efficient general purpose program for assigning sequence reads to genomic features. *Bioinformatics* 30: 923–930. https://doi.org/10.1093/bioinformatics/btt656
- Liu H, Yan Q, Jiang Y, Shi F, Chen J, Cai C et al. (2023) Identification of LcCDPKs and analysis of their expression patterns in response to downy mildew stresses in lychee. *Journal of Fruit Science* 40: 442–456. https://doi.org/10.13925/j.cnki.gsxb.20220307
- Love MI, Huber W and Anders S (2014) Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. *Genome Biology* 15: 550. https://doi.org/10.1186/s13059-014-0550-8
- Mölder F, Jablonski KP, Letcher B, Hall MB, Tomkins-Tinch CH, Sochat V et al. (2021) Sustainable data analysis with Snakemake. *F1000Research* 10: 33. https://doi.org/10.12688/f1000research.29032.2
- Naithani S, Gupta P, Preece J, D’Eustachio P, Elser J, Garg P et al. (2024) Plant Reactome knowledgebase: empowering plant pathway exploration and OMICS data analysis. *Nucleic Acids Research* 52: D1538–D1547. https://doi.org/10.1093/nar/gkad1052
- National Center for Biotechnology Information (NCBI) (2026a) GEO accession GSE201243 and BioProject accession PRJNA830488. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE201243
- National Center for Biotechnology Information (NCBI) (2026b) BioProject accession PRJNA450886. https://www.ncbi.nlm.nih.gov/bioproject/PRJNA450886
- National Center for Biotechnology Information (NCBI) (2026c) GEO accession GSE222651 and BioProject accession PRJNA922966. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222651
- National Center for Biotechnology Information (NCBI) (2026d) GEO accession GSE222650 and BioProject accession PRJNA922965. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222650
- National Center for Biotechnology Information (NCBI) (2026e) GEO accession GSE262200 and BioProject accession PRJNA1090613. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262200
- Nowicka M and Robinson MD (2016) DRIMSeq: a Dirichlet-multinomial framework for multivariate count outcomes in genomics. *F1000Research* 5: 1356. https://doi.org/10.12688/f1000research.8900.2
- Patro R, Duggal G, Love MI, Irizarry RA and Kingsford C (2017) Salmon provides fast and bias-aware quantification of transcript expression. *Nature Methods* 14: 417–419. https://doi.org/10.1038/nmeth.4197
- Pockrandt C, Alzamel M, Iliopoulos CS and Reinert K (2020) GenMap: ultra-fast computation of genome mappability. *Bioinformatics* 36: 3687–3692. https://doi.org/10.1093/bioinformatics/btaa222
- Robinson MD, McCarthy DJ and Smyth GK (2010) edgeR: a Bioconductor package for differential expression analysis of digital gene expression data. *Bioinformatics* 26: 139–140. https://doi.org/10.1093/bioinformatics/btp616
- Sun J, Cao L, Li H, Wang G, Wang S, Li F et al. (2019) Early responses given distinct tactics to infection of *Peronophythora litchii* in susceptible and resistant litchi cultivar. *Scientific Reports* 9: 2810. https://doi.org/10.1038/s41598-019-39100-w
- Sun J, Gao Z, Zhang X, Zou X, Cao L and Wang J (2017) Transcriptome analysis of *Phytophthora litchii* reveals pathogenicity arsenals and confirms taxonomic status. *PLoS ONE* 12: e0178245. https://doi.org/10.1371/journal.pone.0178245
- Van den Berge K, Soneson C, Robinson MD and Clement L (2017) stageR: a general stage-wise method for controlling the gene-level false discovery rate in differential expression and differential transcript usage. *Genome Biology* 18: 151. https://doi.org/10.1186/s13059-017-1277-0
- Wu D, Lim E, Vaillant F, Asselin-Labat ML, Visvader JE and Smyth GK (2010) ROAST: rotation gene set tests for complex microarray experiments. *Bioinformatics* 26: 2176–2182. https://doi.org/10.1093/bioinformatics/btq401
- Wu D and Smyth GK (2012) Camera: a competitive gene set test accounting for inter-gene correlation. *Nucleic Acids Research* 40: e133. https://doi.org/10.1093/nar/gks461
- Yi C, Jiang Y, Shi J, Qu H, Xue S, Duan X et al. (2010) ATP regulation of antioxidant properties and phenolics in litchi fruit during browning and pathogen infection. *Food Chemistry* 118: 42–47. https://doi.org/10.1016/j.foodchem.2009.04.074
- Zhuang E (2026) Supplemental material for “Cultivar-dependent transcriptional responses of lychee to *Peronophythora litchii*: a registered genome-wide analysis.” Zenodo. https://zenodo.org/records/22436625

# Tables

## Table 1. Cross-context-supported genes and response reversals in the primary external evaluation

Discovery effects are Yurong1-minus-Guiwei interaction log2 fold changes in leaf; external effects are Heiye-minus-Guiwei interaction log2 fold changes in pericarp at 24 h with 95% confidence intervals (CI). All *q*-values are Benjamini–Hochberg adjusted (discovery: genome-wide; external: across the frozen candidate-by-contrast family).

| Gene | Annotation | Discovery log2FC | Discovery *q* | External log2FC (95% CI) | External *q* | Outcome |
|---|---|---:|---:|---:|---:|---|
| LITCHI005518 | Alpha-xylosidase 1 | +0.64 | 0.025 | +0.67 (+0.32 to +1.02) | 0.007 | Supported |
| LITCHI001963 | Uncharacterized; one-to-one rice ortholog | −1.41 | 0.024 | −0.94 (−1.43 to −0.46) | 0.007 | Supported |
| LITCHI030761 | Caffeoylshikimate esterase | −0.92 | 0.040 | +1.31 (+0.78 to +1.85) | <0.001 | Reversed |
| LITCHI029534 | Thiamine thiazole synthase 2 | +1.48 | 0.002 | −1.04 (−1.61 to −0.48) | 0.010 | Reversed |
| LITCHI021860 | Phosphatidylinositol 4-kinase gamma 2 | −0.65 | 0.032 | +0.97 (+0.39 to +1.54) | 0.029 | Reversed |
| LITCHI008313 | Beta-glucosidase 44 | +0.90 | 0.045 | −1.12 (−1.81 to −0.44) | 0.034 | Reversed |
| LITCHI001700 | Fe(II)/2-oxoglutarate-dependent dioxygenase 4 | +3.70 | 0.033 | −2.00 (−3.24 to −0.77) | 0.035 | Reversed |

## Table 2. Twelve Tier B genes prioritized by complete internal robustness

Discovery effects are interaction log2 fold changes (Yurong1 response minus Guiwei response). External columns give the 24-h pericarp estimate with 95% CI and family-adjusted *q*. All nine measurable genes retained the discovery direction. NM, not measurable.

| Gene | Family-level annotation | Discovery log2FC | Genome-wide *q* | External log2FC (95% CI) | External *q* |
|---|---|---:|---:|---:|---:|
| LITCHI014613 | Sugar transporter ERD6-like 16 | +3.69 | <0.001 | +0.60 (−0.04 to +1.25) | 0.270 |
| LITCHI015982 | WAT1-related protein | +3.43 | <0.001 | +0.77 (+0.07 to +1.48) | 0.180 |
| LITCHI005805 | Phosphomannomutase/phosphoglucomutase | +2.07 | <0.001 | NM | — |
| LITCHI028926 | Exonuclease 1 | +1.90 | <0.001 | +0.32 (−0.63 to +1.28) | 0.830 |
| LITCHI016077 | Serine carboxypeptidase 24 | +1.81 | <0.001 | +0.23 (−1.05 to +1.51) | 0.890 |
| LITCHI013915 | 1,4-alpha-glucan-branching enzyme 3 | +1.58 | <0.001 | +0.53 (+0.10 to +0.95) | 0.130 |
| LITCHI021546 | Homeobox-DDT domain protein RLT3 | +1.31 | <0.001 | +0.12 (−0.30 to +0.54) | 0.830 |
| LITCHI022605 | Ribonuclease J | +0.74 | <0.001 | +0.14 (−0.34 to +0.62) | 0.830 |
| LITCHI028717 | BAG-family chaperone regulator 4 | −0.91 | <0.001 | −1.20 (−2.52 to +0.12) | 0.290 |
| LITCHI008721 | Unannotated protein | −1.91 | <0.001 | NM | — |
| LITCHI015740 | Putative lipid-transfer protein DIR1 | −1.96 | <0.001 | −0.21 (−1.10 to +0.69) | 0.880 |
| LITCHI010877 | Cytochrome P450 81Q32 | −2.77 | <0.001 | NM | — |

# Figure Legends

## Figure 1. Study cohorts, discovery quality control and expression structure

(A) Five public cohorts with prespecified roles and deposited library counts. (B) Per-library technical quality in the discovery cohort: fastp read survival, STAR unique-alignment rate and Salmon mapping rate. All 12 libraries passed the fixed inclusion gates. (C) Principal-component analysis separates cultivar and infection status. Each cultivar–treatment group contained three deposited libraries. GW, Guiwei; YR, Yurong1; inf., infected.

## Figure 2. Genome-wide discovery and assessment of exploratory candidates

(A) Cultivar-by-infection interaction effects across 19,445 expressed genes; 262 genes met the statistical threshold and 206 remained after uniform mapping and gene-model quality control. (B) Genome-wide interaction estimates with 95% CI for the 18 exploratory candidates; orange denotes candidates excluded by uniform-mappability control. Within-cultivar infection responses appear in Supporting Data Table S14. (C) Candidate prioritization from tested genes to the internally robust set. *q*, Benjamini–Hochberg-adjusted probability.

## Figure 3. Internal robustness and context-dependent external responses

(A) Candidates retained by each prespecified robustness gate, their conjunction and the observed-mapping gate. (B) The 16-gene internally robust set and two cross-context-supported genes are complementary candidate groups. (C) Discovery interaction effects plotted against primary external effects (Heiye response minus Guiwei response, pericarp, 24 h), highlighting supported, opposite-direction and internally robust genes. The diagonal is a visual reference; equal effects are not expected across different tissues and cultivar contrasts.

## Figure 4. Pathway robustness and context-dependent signature responses

(A) Discovery normalized enrichment scores for six frozen pathways; circadian rhythm passed every internal gate, whereas none met the primary external criteria. (B) The frozen signed 206-gene score across six non-exploratory external contrasts; filled points denote *q*<0.05. The exploratory PRJNA1090613 estimate is shown in Supporting Information Figure S3. NES, normalized enrichment score; CI, confidence interval.

## Figure 5. Functional annotation, orthogonal analyses and candidate prioritization

(A) Annotation status of the 206 quality-controlled genes. (B) Registered promoter-motif robustness and the small-RNA reference gate. (C) Deterministic evidence tiers over all 268 frozen entities. TF, transcription factor; TFBS, transcription-factor binding site; FIMO, Find Individual Motif Occurrences; miRNA, microRNA.
