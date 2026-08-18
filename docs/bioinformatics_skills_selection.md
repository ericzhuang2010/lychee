# Bioinformatics Skills Selection for the Lychee Manuscript

Curated selection of skills (zip files) relevant to the lychee–*Phytophthora litchii*
transcriptomic reanalysis, mapped to the analyses in
`docs/lychee_manuscript_improvement_plan.md` and the reviewer concerns in
`docs/review_feedback.txt` (missing FDR/genome-wide inference, provenance/QC,
over-speculative motif/mechanism claims, weak introduction/discussion).

## 1. Core (always needed — 7)

```
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/bioinformatics-paper-orchestrator.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/exploratory-data-analysis.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/paper-lookup.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/scientific-brainstorming.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/scientific-critical-thinking.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/scientific-visualization.zip
/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-core-skills/statistical-analysis.zip
```

## 2. Recommended (directly map to the plan)

Base path: `/Users/rzhuang/Documents/VscodeProjects/lychee/bioinformatics-skills/bioinformatics-skills-download/chatgpt-upload/`

Data acquisition & references (§2, §3.1–3.2, §9):

```
openai/ncbi-entrez-skill.zip
openai/ncbi-datasets-skill.zip
openai/ensembl-skill.zip
aipoch/ena-database.zip
```

RNA-seq processing, QC, reproducible pipeline (§3.2, §3.13):

```
kdense/bulk-rnaseq.zip
kdense/pysam.zip
kdense/deeptools.zip
kdense/nextflow.zip
```

Differential expression, factorial/interaction models, statistics (§3.3–3.7 — the FDR / genome-wide fix reviewers demanded):

```
kdense/pydeseq2.zip
aipoch/differential-expression-analysis.zip
aipoch/gene-protein-expression-matrix-normalization.zip
kdense/statsmodels.zip
```

Expression QC, dimensionality reduction, clustering (§1.4, §3.2, Fig 1):

```
aipoch/pca-dimensionality-reduction.zip
aipoch/hierarchical-clustering-plot.zip
```

Pathway / gene-set enrichment (§3.9, Fig 4):

```
kdense/pathway-enrichment.zip
aipoch/gokegg.zip
openai/reactome-skill.zip
openai/quickgo-skill.zip
kdense/gget.zip
```

Coexpression network (§3.10, Fig 5):

```
aipoch/wgcna-analysis.zip
kdense/networkx.zip
```

Annotation, orthology, sequence/promoter handling (§3.8, §3.11):

```
kdense/biopython.zip
openai/ncbi-blast-skill.zip
openai/uniprot-skill.zip
kdense/phylogenetics.zip
```

Visualization (§4.4):

```
kdense/matplotlib.zip
```

Literature, writing, review-compliance, claim discipline (§1, §5, addresses "too brief intro", "overly speculative", format/keyword issues):

```
kdense/literature-review.zip
aipoch/multi-database-literature-collector.zip
kdense/scientific-writing.zip
aipoch/methods-section-writer.zip
kdense/citation-management.zip
aipoch/target-journal-matcher.zip
kdense/peer-review.zip
aipoch/reporting-guideline-compliance-checker.zip
aipoch/paper-to-claim-verifier.zip
aipoch/result-reliability-checker.zip
```

## 3. Optional (situational — pull in as specific tasks arise)

```
aipoch/batch-effect-correction.zip          # cross-study integration (§3.7)
aipoch/umap-tsne-analysis.zip               # extra QC ordination
aipoch/gsva-analysis-and-visualization.zip  # single-sample enrichment alt
aipoch/validation-strategy-designer.zip     # cross-dataset validation framing
aipoch/sample-size-and-power-planning-assistant.zip
kdense/statistical-power.zip
kdense/scikit-learn.zip
kdense/scikit-bio.zip
kdense/bioservices.zip                       # KEGG/UniProt/etc API access
kdense/polars-bio.zip                        # genomic-interval ops (promoter extraction from GFF)
openai/string-skill.zip                      # candidate PPI context
openai/ncbi-pmc-skill.zip                    # full-text lit
openai/rnacentral-skill.zip                  # only if small-RNA/miRNA dataset (§2.4) is used
openai/biorxiv-skill.zip                     # preprints
kdense/venue-templates.zip
kdense/pyzotero.zip
aipoch/figure-first-paper-reader.zip
aipoch/high-value-paper-screener.zip
aipoch/biomedical-search-strategy-builder.zip
```

## Notes on what was deliberately excluded and one gap

- **Excluded whole families** as off-topic for a plant-pathology bulk-RNA-seq
  reanalysis: single-cell (`scanpy`, `anndata`, `scvi-tools`, `scvelo`,
  `cellxgene*`, spatial, `histolab`); human immune/oncology (`cibersort`,
  `estimate-immune-score`, `ssgsea-immune-infiltration`, `immune-pathway-analysis`,
  all `*hub-gene*`/`prognostic`/`nomogram`/`scikit-survival`); human
  genetics/variants/GWAS/PheWAS (`clinvar*`, `gnomad`, `gwas-catalog`,
  `gtex/eqtl*`, `*phewas*`, `cbioportal`, `civic`, `tiledbvcf`, `cnv-caller`);
  proteomics/metabolomics/structure/chem (`pyopenms`, `matchms`, `hmdb`,
  `metabolights`, `pride`, `alphafold`, `rcsb-pdb`, `diffdock`, `chembl`,
  `pubchem`, etc.); and cloud platforms (`dnanexus`, `latchbio`, `lamindb`).
- **Duplicates** (`biopython`, `pysam`, `pydeseq2`, `matplotlib`,
  `literature-review`, `bioservices`, `scikit-bio` exist in both AIPOCH and
  K-Dense): one source each is chosen to avoid install collisions — mostly
  K-Dense for generic tools, AIPOCH for workflow-style analysis skills.
- **Gap:** the plan's §3.11 promoter/motif work (JASPAR/CIS-BP PWMs,
  AME/STREME/Tomtom/FIMO) has **no dedicated MEME-suite skill** in this
  collection. `biopython` covers PWM/motif I/O, but MEME Suite tools would be
  run directly. Worth flagging since motif rigor is central to the reviewer
  rebuttal.
