# Revised Computational Discovery and Validation Plan for the Lychee–*Phytophthora litchii* Study

## Purpose

This plan is designed to produce both:

1. a genuinely new computational discovery; and
2. credible validation without generating new laboratory data.

The plan replaces the previous “analyze everything, then rank candidates” approach with a strict discovery/validation firewall:

- discovery is performed on one locked dataset;
- discovery results are frozen before external outcomes are examined;
- alternative tools on the same data are called robustness checks;
- independent public datasets test transportability or replication;
- published evidence and small-RNA data provide orthogonal support;
- all claims use precise evidence vocabulary.

## Recommended central discovery

Primary discovery:

> A genome-wide Guiwei–Yurong cultivar-by-infection interaction signature in lychee leaves.

Primary validation question:

> Does the frozen signature retain its expected direction and pathway behavior across an independent Guiwei–Heiye fruit time course and other public lychee infection datasets?

Conditional secondary discovery:

> Cultivar-dependent transcript-usage changes that are not visible in gene-level differential-expression results.

This secondary analysis should proceed only if transcript annotation, read quality, and mappability pass a preflight gate.

## Evidence vocabulary

Use these terms consistently:

- **Discovered:** passes the locked primary analysis in GSE201243.
- **Robust:** survives alternative methods on the same biological samples.
- **Replicated:** passes a preregistered test of the same estimand in independent biological samples.
- **Cross-context supported:** same direction or signature behavior in different cultivars, tissue, or time.
- **Orthogonally supported:** supported by another data modality or independent published evidence.
- **Exploratory:** analyzed after seeing outcomes or without sufficient provenance/power.

Do not use “validated resistance gene,” “functional motif,” or “mechanism.”

## Stage map

0. Preflight and asset recovery
1. Freeze protocol, novelty claim, dataset roles, and acceptance criteria
2. Acquire tools, references, and discovery data
3. Verify sample provenance and dataset eligibility
4. Process the discovery dataset and complete QC
5. Run and freeze the primary discovery
6. Run internal robustness analyses
7. Open and evaluate external datasets
8. Validate pathways/signatures and optional transcript usage
9. Add orthogonal annotation, small-RNA, motif, and literature support
10. Assign deterministic evidence statuses and candidate tiers
11. Produce figures and tables
12. Write the paper in standard bioinformatics-paper structure
13. Release data/code and perform final review

---

# Stage 0 — Preflight and asset recovery

## Goal

Ensure the plan can run from the current filesystem and available compute without silently assuming missing files.

## Step 0.1 — Check local inputs

Check for:

- manuscript PDF/DOCX;
- reviewer feedback;
- S2 workflow ZIP;
- S3 GSE262200 workflow ZIP;
- prior figures;
- available disk/RAM/CPU;
- required accounts or restricted resources.

Current review found that the manuscript PDF and S2/S3 ZIP files were not present at the paths referenced by the previous execution plan. Treat this as a blocking preflight item rather than allowing later commands to fail.

Example preflight script:

```bash
export PROJECT="/Users/rzhuang/Documents/VscodeProjects/lychee"
export ARCHIVE="/Users/rzhuang/Documents/research/lychee"
cd "$PROJECT"

python analysis/scripts/00_preflight.py \
  --project "$PROJECT" \
  --archive "$ARCHIVE" \
  --required analysis/config/required_inputs.yaml \
  --report results/audit/preflight_report.tsv
```

Required checks:

- path exists;
- expected file type;
- nonzero size;
- checksum if known;
- URL responds;
- ≥150 GiB free before processing an active study;
- approximately 200 GB total workspace available, requiring staged processing and cleanup;
- ≥16 CPU and preferably ≥64 GB RAM for full workflow.

## Step 0.2 — Use the 200-GB storage strategy

The plan is feasible with 200 GB only when datasets are processed sequentially and large intermediates are removed after verification.

Verified compressed FASTQ sizes:

- GSE201243 / PRJNA830488: approximately 37 GiB;
- PRJNA450886: approximately 64 GiB;
- GSE222651 / PRJNA922966: approximately 54 GiB;
- GSE222650 / PRJNA922965: approximately 2.4 GiB;
- GSE262200 / PRJNA1090613: approximately 32 GiB;
- all compressed FASTQ together: approximately 190 GiB.

Do not store all datasets simultaneously.

### Required processing order

1. Download/process GSE201243.
2. Freeze discovery and robustness results.
3. Remove its trimmed FASTQ and BAM files after count/QC verification.
4. Download/process PRJNA450886.
5. Remove its large intermediates.
6. Download/process GSE222651.
7. Use the GSE262200 deposited count matrix unless raw reprocessing becomes essential.
8. Defer the optional small-RNA branch until adequate free space remains.

### Peak-space budget

Reserve approximately:

- 30–40 GiB for references, indexes, environments, and results;
- 37–64 GiB for the active study’s compressed FASTQ;
- 15–40 GiB for one sample/batch of trimmed reads, BAM, and STAR temporary files;
- at least 30 GiB safety margin.

Expected peak: approximately 150–180 GiB.

### Concurrency limit

Process one large alignment at a time:

```bash
export MAX_CONCURRENT_ALIGNMENTS=1
```

Configure Snakemake resources so only one STAR sorting job runs concurrently.

### Cleanup policy

Before deleting anything:

1. verify FASTQ MD5;
2. verify BAM/count/QC completion;
3. checksum the count matrix and QC report;
4. confirm the study can be redownloaded from ENA;
5. record cleanup in `analysis/logs/storage_cleanup.tsv`.

Retain:

- manifests and MD5;
- frozen references;
- count/transcript matrices;
- QC reports/logs;
- statistical results;
- scripts/environments.

Delete after validation:

- trimmed FASTQ;
- STAR temporary directories;
- BAM files not needed for mapping-sensitivity analysis.

If an alignment must be retained, convert BAM to CRAM:

```bash
samtools view \
  -C \
  -T data/reference/combined/lychee_pathogen.fa \
  -o sample.cram \
  sample.bam

samtools index sample.cram
```

Delete the BAM only after CRAM validation.

### Avoid large local annotation databases

Do not install full InterPro/eggNOG databases on the 200-GB workspace.

Use:

- shared institutional storage;
- a remote server/cloud instance;
- web services;
- targeted annotation of frozen candidates when necessary.

Check free space before every study:

```bash
df -h "/Users/rzhuang/Documents/VscodeProjects/lychee"
du -sh data analysis results
```

Block a new download if less than approximately 150 GiB is free.

## Step 0.3 — Recover or reconstruct missing workflows

S2 is available from the manuscript’s Zenodo record:

- [https://zenodo.org/records/20007391](https://zenodo.org/records/20007391)

If S3 is unavailable locally, reconstruct it from the GSE262200 count matrix and the revised locked analysis specification. Do not delay the project solely to recover a template.

## Step 0.4 — Create a synthetic test fixture

Do not use GSE262200 biological outcomes to test code if it may serve as a holdout.

Create a small simulated count matrix with:

- 2 cultivars;
- 2 treatments;
- 3 replicates/cell;
- known interaction genes;
- known null genes;
- one deliberately confounded metadata fixture that must fail validation.

Commands:

```bash
Rscript analysis/tests/create_synthetic_fixture.R \
  --seed 20260718 \
  --outdir analysis/tests/fixtures

Rscript analysis/tests/test_interaction_pipeline.R \
  --fixture analysis/tests/fixtures \
  --expected analysis/tests/fixtures/expected_results.tsv
```

## Completion gate

- all primary inputs are present or have a reconstruction route;
- resource requirements are satisfied;
- the synthetic fixture produces expected interaction signs/q-value ordering;
- confounded metadata are rejected automatically.

---

# Stage 1 — Freeze protocol, novelty claim, dataset roles, and acceptance criteria

## Goal

Prevent circular validation and post hoc candidate selection.

## Step 1.1 — Create a time-stamped prospective protocol

Because the original manuscript results are already known, call this:

> a time-stamped prospective analysis protocol for a retrospective reanalysis.

Create:

`analysis/preregistration/discovery_validation_protocol_v1.md`

Record prior knowledge:

- current 17/117 DEG counts;
- old 18 candidates;
- known WRKY/CDPK papers;
- known public datasets;
- any previously viewed GSE262200 results.

Record locked choices:

- discovery dataset;
- primary coefficient;
- count filter;
- effect threshold;
- pathway collection;
- candidate rule;
- robustness criteria;
- external dataset roles;
- external pass/fail criteria;
- fallback if no gene passes.

Checksum:

```bash
shasum -a 256 \
  analysis/preregistration/discovery_validation_protocol_v1.md \
  > analysis/preregistration/discovery_validation_protocol_v1.sha256
```

Maintain:

`analysis/preregistration/amendments.tsv`

with date, reason, change, and whether it occurred before or after outcomes were viewed.

## Step 1.2 — Freeze dataset roles

### Discovery

**GSE201243 / PRJNA830488**

- Guiwei and Yurong1 leaves;
- challenge/mock;
- 24 h;
- three deposited libraries/cell;
- 12 paired-end runs;
- SRR18856598–SRR18856609.

Sources:

- [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE201243)
- [ENA](https://www.ebi.ac.uk/ena/browser/view/PRJNA830488)

### Primary external cross-context evaluation

**PRJNA450886**

- Guiwei and Heiye fruit pericarp;
- challenge/mock;
- 6, 24, 48 h;
- 36 runs;
- SRR8297698–SRR8297733.

Sources:

- [BioProject](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA450886)
- [paper](https://doi.org/10.1038/s41598-019-39100-w)

Primary external contrast:

- cultivar×infection at 24 h.

Secondary:

- 6-h and 48-h temporal behavior.

### Generic infection/tissue transfer

**GSE222651 / PRJNA922966**

- Feizixiao leaf/fruit;
- challenge/mock;
- 24 h;
- 12 long-RNA runs;
- SRR23050939–SRR23050950.

Sources:

- [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222651)
- [ENA](https://www.ebi.ac.uk/ena/browser/view/PRJNA922966)

This cannot validate a cultivar interaction.

### Orthogonal modality

**GSE222650 / PRJNA922965**

- parallel small-RNA component;
- 12 runs;
- SRR23050908–SRR23050919.

Sources:

- [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222650)
- [ENA](https://www.ebi.ac.uk/ena/browser/view/PRJNA922965)

Treat GSE222650/651 as one biological cohort.

### Quarantined potential interaction holdout

**GSE262200 / PRJNA1090613**

- GW and SFZ leaves;
- challenge/mock;
- 12 runs;
- SRR28413505–SRR28413516;
- deposited count matrix.

Sources:

- [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262200)
- [BioProject](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1090613)

Use as a holdout only if, before outcomes are opened:

- sampling time is confirmed;
- SFZ identity/resistance phenotype is documented;
- biological-unit independence is verified;
- annotation/ID compatibility is adequate.

Otherwise classify as development or exploratory data.

## Step 1.3 — Freeze discovery thresholds

Recommended gene-level discovery:

- BH q<0.05;
- absolute interaction log2FC ≥ log2(1.5);
- adequate counts;
- uniquely interpretable gene model;
- no severe mapping-bias flag.

Fallback if no gene passes:

- report the null;
- run the prespecified pathway-level interaction signature;
- do not create a top-gene list from raw P values.

## Step 1.4 — Freeze validation thresholds

Internal robustness:

- signed-statistic Spearman \(\rho\) ≥0.85;
- candidate sign agreement in all pipelines;
- absolute LFC difference ≤0.5;
- q<0.10 in DESeq2 and edgeR;
- same sign in all leave-one-out fits;
- q<0.10 in at least 10/12 leave-one-out fits;
- no leading-candidate mappability failure.

External gene-level support:

- same prespecified direction;
- BH q<0.05 across frozen candidate×contrast tests;
- absolute LFC ≥log2(1.5);
- 95% CI excludes zero.

Pathway/signature support:

- same frozen gene set;
- same direction;
- q<0.05 in at least two independent studies;
- removing the largest leading-edge gene leaves q<0.10;
- score exceeds 95% of matched random sets.

These are recommended thresholds and must be fixed before outcomes are opened.

## Completion gate

The protocol, roles, thresholds, and fallback are checksummed before discovery analysis.

---

# Stage 2 — Acquire tools, references, and discovery data

## Goal

Install versioned tools and acquire only the resources needed for discovery and blinded external processing.

## Step 2.1 — Core workflow tools

Recommended installation:

```bash
micromamba create -n lychee-discovery -c conda-forge -c bioconda \
  python r-base snakemake-minimal \
  ncbi-datasets-cli sra-tools \
  fastqc multiqc fastp \
  star salmon subread samtools rseqc \
  bedtools gffread seqkit diamond \
  meme aria2 pigz ripgrep

micromamba activate lychee-discovery
```

Sources:

- micromamba: [https://mamba.readthedocs.io/](https://mamba.readthedocs.io/)
- Bioconda: [https://bioconda.github.io/](https://bioconda.github.io/)
- Snakemake: [https://snakemake.readthedocs.io/](https://snakemake.readthedocs.io/)
- STAR: [https://github.com/alexdobin/STAR](https://github.com/alexdobin/STAR)
- Salmon: [https://combine-lab.github.io/salmon/](https://combine-lab.github.io/salmon/)
- featureCounts/Subread: [https://subread.sourceforge.net/](https://subread.sourceforge.net/)
- MultiQC: [https://multiqc.info/](https://multiqc.info/)

## Step 2.2 — R/Bioconductor tools

```bash
Rscript - <<'RS'
if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", repos = "https://cloud.r-project.org")
}

BiocManager::install(c(
  "DESeq2", "edgeR", "limma", "tximport",
  "apeglm", "IHW", "fgsea", "stageR",
  "DRIMSeq", "DEXSeq", "clusterProfiler",
  "ComplexHeatmap"
), ask = FALSE, update = FALSE)

install.packages(c(
  "tidyverse", "data.table", "patchwork",
  "ggrepel", "WGCNA", "metafor"
), repos = "https://cloud.r-project.org")
RS
```

Sources:

- Bioconductor: [https://bioconductor.org/](https://bioconductor.org/)
- DESeq2: [https://bioconductor.org/packages/DESeq2](https://bioconductor.org/packages/DESeq2)
- edgeR: [https://bioconductor.org/packages/edgeR](https://bioconductor.org/packages/edgeR)
- limma/camera: [https://bioconductor.org/packages/limma](https://bioconductor.org/packages/limma)
- fgsea: [https://bioconductor.org/packages/fgsea](https://bioconductor.org/packages/fgsea)
- DRIMSeq: [https://bioconductor.org/packages/DRIMSeq](https://bioconductor.org/packages/DRIMSeq)
- stageR: [https://bioconductor.org/packages/stageR](https://bioconductor.org/packages/stageR)

Freeze:

```bash
micromamba env export -n lychee-discovery \
  > analysis/envs/lychee-discovery.yml

Rscript -e 'writeLines(capture.output(sessionInfo()), "analysis/envs/R_sessionInfo.txt")'
```

## Step 2.3 — Annotation/pathway/motif tools

- InterProScan: [https://www.ebi.ac.uk/interpro/download/](https://www.ebi.ac.uk/interpro/download/)
- eggNOG-mapper: [https://github.com/eggnogdb/eggnog-mapper](https://github.com/eggnogdb/eggnog-mapper)
- DIAMOND: [https://github.com/bbuchfink/diamond](https://github.com/bbuchfink/diamond)
- OrthoFinder: [https://github.com/davidemms/OrthoFinder](https://github.com/davidemms/OrthoFinder)
- MEME Suite: [https://meme-suite.org/](https://meme-suite.org/)
- JASPAR Plants: [https://jaspar.elixir.no/](https://jaspar.elixir.no/)
- Plant Reactome: [https://plantreactome.gramene.org/](https://plantreactome.gramene.org/)
- Gene Ontology: [https://current.geneontology.org/ontology/go-basic.obo](https://current.geneontology.org/ontology/go-basic.obo)

Record release, checksum, license, and retrieval date for every resource.

## Step 2.4 — Host reference

Sequence:

- SCAU_Lch_v2.0, GCA_019925255.1
- [NCBI Datasets](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_019925255.1/)

Matched assembly/annotation package:

- [Mendeley DOI 10.17632/kggzfwpdr9.1](https://data.mendeley.com/datasets/kggzfwpdr9/1)
- [Sapindaceae Genome Database](http://www.sapindaceae.com/Download.html)

Choose one matched FASTA/GFF/CDS/protein bundle and require:

- contig-name and length consistency;
- coordinate bounds;
- unique IDs;
- valid feature hierarchy;
- CDS/protein extraction concordance;
- frozen canonical-transcript rules.

## Step 2.5 — Pathogen reference

- GWH assembly GWHAOTU00000000/GWHAOTU00000000.1
- [https://ngdc.cncb.ac.cn/gwh/Assembly/GWHAOTU00000000](https://ngdc.cncb.ac.cn/gwh/Assembly/GWHAOTU00000000)

Use for competitive mapping and exploratory pathogen-read assignment.

## Step 2.6 — Acquire discovery reads

Generate ENA manifest:

```bash
ACC="PRJNA830488"

curl -fL \
  "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${ACC}&result=read_run&fields=study_accession,sample_accession,experiment_accession,run_accession,sample_title,experiment_title,library_layout,instrument_model,read_count,base_count,fastq_ftp,fastq_md5&format=tsv" \
  -o "analysis/metadata/${ACC}.tsv"
```

Download FASTQ from the `fastq_ftp` column with aria2c and verify every `fastq_md5`.

## Step 2.7 — Quarantine external outcomes

With the 200-GB limit, do not download external FASTQ before Stage 5 is frozen. Download and checksum metadata/manifests only.

After discovery freeze, download one external study at a time into:

- `data/active_holdout/PRJNA450886/`;
- then, after cleanup, `data/active_holdout/PRJNA922966/`;
- download GSE262200 raw reads only if it passes holdout eligibility and count-matrix analysis is insufficient.

Create:

`analysis/preregistration/HOLDOUT_DO_NOT_ANALYZE.txt`

## Completion gate

Tool versions are frozen, references pass compatibility checks, discovery FASTQ pass MD5, and holdout outcomes remain unopened.

---

# Stage 3 — Verify sample provenance and dataset eligibility

## Goal

Determine which datasets can support inferential statistics and which must remain descriptive.

## Step 3.1 — Build a biological-unit registry

Create:

`analysis/metadata/biological_unit_registry.tsv`

Fields:

- study;
- BioProject/GEO/BioSample/run;
- cultivar/genotype;
- tree/orchard/source organism;
- harvest;
- pooled material;
- extraction;
- library;
- technical replicate relationship;
- treatment;
- tissue;
- time;
- batch;
- independence status;
- evidence source.

## Step 3.2 — Reconcile metadata

Compare:

- GEO/GSM;
- SRA/ENA/BioSample;
- paper methods;
- supplementary files.

Priority conflicts:

- GSE201243 instrument/cultivar/extraction descriptions;
- source-tree independence;
- PRJNA450886 fruit-pool independence;
- GSE222650/651 pairing;
- GSE262200 time and SFZ phenotype.

## Step 3.3 — Contact submitters

Ask only for fields needed for eligibility. Archive correspondence and nonresponses.

## Step 3.4 — Assign eligibility

Categories:

- **Inferential:** ≥3 verified independent units/cell, full-rank model, no perfect confounding.
- **Cross-context:** independent but different estimand.
- **Descriptive:** independence unresolved or insufficient.
- **Ineligible:** technical duplication/confounding prevents meaningful inference.

If GSE201243 independence cannot be verified:

- report this as a primary limitation;
- present q values as model-based evidence conditional on deposited-library independence;
- avoid population-level generalization.

## Completion gate

Dataset roles and eligibility are frozen before discovery statistics are generated.

---

# Stage 4 — Process discovery data and complete QC

## Goal

Produce one frozen count matrix and technical-quality report for GSE201243 without accessing external outcomes.

## Step 4.1 — Raw-read QC and trimming

Run:

- FastQC;
- MultiQC;
- fastp with adapter auto-detection;
- no aggressive trimming without documented need.

Outputs:

- raw/trimmed QC;
- read-length/adapters;
- duplication;
- overrepresented sequences;
- per-library depth.

## Step 4.2 — Combined host/pathogen alignment

Build a combined reference with `HOST_` and `PATH_` prefixes.

Run STAR two-pass.

Record:

- unique/multiple mapping;
- mismatch rate;
- host/pathogen/ambiguous fractions;
- cultivar-specific mapping differences;
- per-gene coverage for leading loci later.

## Step 4.3 — Count genes and quantify transcripts

Primary:

- featureCounts from STAR BAMs.

Sensitivity:

- Salmon transcript quantification;
- tximport gene summarization.

Generate:

- integer count matrix;
- transcript abundance;
- transcript-to-gene map;
- mappability/coverage metrics.

## Step 4.4 — Expression QC

Required:

- VST PCA;
- sample distances;
- replicate correlations;
- detected genes;
- library sizes;
- Cook’s distances;
- model-matrix rank;
- batch/confounding checks.

Exclude a library only for a preregistered technical reason. Preserve all-sample and exclusion sensitivity results.

## Step 4.5 — Mapping-bias preflight

For all potential leading loci:

- unique-mappability;
- mismatch burden;
- coverage uniformity;
- cultivar-specific coverage loss;
- host/pathogen ambiguity.

Plan variant-aware/reference-swap analysis only for loci that enter the frozen discovery set.

## Completion gate

The discovery matrix, metadata, QC, and filter rule are frozen and checksummed.

---

# Stage 5 — Run and freeze the primary discovery

## Goal

Identify a new cultivar-dependent response signature without using external outcomes.

## Step 5.1 — Primary gene-level interaction

Model:

```r
design = ~ cultivar + treatment + cultivar:treatment
```

Primary coefficient:

`infection effect in Yurong - infection effect in Guiwei`

Run:

- Wald test for all filtered genes;
- full-versus-reduced LRT;
- within-cultivar infection contrasts;
- shrunken effects for display only.

Required outputs:

- all genes with base mean, LFC, SE, P, q;
- q<0.05 and effect-threshold genes;
- normalized counts;
- old-18 audit.

## Step 5.2 — Primary pathway interaction signature

Use one frozen versioned collection.

Primary:

- fgseaMultilevel on signed interaction statistics.

Sensitivity later:

- camera;
- roast;
- matched random sets.

Freeze:

- pathway names;
- gene members;
- direction;
- weights or signed statistics;
- leading-edge genes.

## Step 5.3 — Build the signed discovery signature

If gene-level discoveries pass:

- include only genes meeting q/effect/mappability criteria;
- define weight as signed shrunken interaction LFC or another preregistered statistic;
- standardize direction so positive means stronger response in the resistant comparator.

If no gene passes:

- set the gene signature to empty;
- use only the frozen pathway-level fallback;
- do not use arbitrary top-N genes.

## Step 5.4 — Conditional differential transcript usage

Proceed only if:

- transcript annotation is consistent;
- ≥2 expressed isoforms exist for enough genes;
- transcript mappability is adequate;
- Salmon bootstrap/quantification diagnostics pass.

Use:

- DRIMSeq for transcript proportions;
- stageR for gene/transcript-level error control;
- DEXSeq as sensitivity.

Primary DTU question:

> Does transcript usage show a cultivar×infection interaction?

Recommended discovery criterion:

- stage-wise OFDR<0.05;
- adequate transcript abundance;
- change not explained by low mappability.

Freeze significant genes, transcript IDs, and expected external directions.

## Step 5.5 — Freeze discovery outputs

Create:

- `results/discovery/frozen_genes.tsv`
- `results/discovery/frozen_pathways.tsv`
- `results/discovery/frozen_signature.tsv`
- `results/discovery/frozen_dtu.tsv`
- `results/discovery/discovery_summary.md`

Checksum:

```bash
shasum -a 256 results/discovery/frozen_* \
  > results/discovery/frozen_results.sha256
```

Record the timestamp at which external outcomes may be opened.

## Completion gate

Discovery genes/pathways/signature/DTU results are immutable except documented error correction.

---

# Stage 6 — Internal robustness analyses

## Goal

Determine whether discovery depends on one computational choice.

## Step 6.1 — Quantification robustness

Compare:

- STAR–featureCounts;
- Salmon–tximport;
- optional HISAT2–featureCounts if compute permits.

Pass:

- signed-statistic \(\rho\)≥0.85;
- frozen-gene sign agreement;
- |LFC difference|≤0.5.

## Step 6.2 — Statistical robustness

Compare:

- DESeq2 Wald;
- edgeR quasi-likelihood;
- DESeq2 LRT for overall interaction.

Pass:

- same candidate direction;
- q<0.10 in DESeq2 and edgeR.

## Step 6.3 — Filter robustness

Compare:

- ≥10 counts in ≥3 samples;
- CPM>1 in ≥3 samples.

Report genes/pathways sensitive to filtering.

## Step 6.4 — Leave-one-library-out

Run all 12 omissions.

Pass:

- same sign in 12/12 fits;
- q<0.10 in at least 10/12.

## Step 6.5 — Mapping sensitivity

For frozen loci:

- inspect coverage/mismatch;
- assess unique mappability;
- use WASP filtering, reference-swap, or variant-aware sensitivity where feasible;
- retire loci with strong reference-bias evidence.

## Step 6.6 — Pathway robustness

Run:

- camera with expression/design/contrast;
- roast;
- leading-edge deletion;
- matched random sets.

Separate “discovered” and “robust” statuses.

## Completion gate

Frozen discoveries receive a robustness status without using external datasets.

---

# Stage 7 — Open and evaluate external datasets

## Goal

Test frozen discovery results using fixed external scripts and criteria.

## Step 7.1 — Unlock external data

Record:

- discovery-freeze checksum;
- unlock date/time;
- external scripts/config versions;
- no tuning permitted after outcomes appear.

## Step 7.2 — PRJNA450886 primary external evaluation

Download and process raw reads against the same frozen host reference. Run samples sequentially, generate counts/QC, and remove trimmed FASTQ/BAM after verified outputs are checksummed.

Model:

```r
design = ~ cultivar * treatment * time
```

Primary external contrast:

- Guiwei–Heiye cultivar×infection at 24 h.

Secondary:

- 6 h;
- 48 h;
- three-way temporal interaction.

Test:

- frozen discovery genes only for confirmatory external evaluation;
- frozen signature score;
- frozen pathways;
- frozen DTU events where transcripts are measurable.

Do not redefine candidates using PRJNA450886 results.

## Step 7.3 — GSE222651 tissue transfer

Start only after PRJNA450886 large intermediates have been removed and free space is again ≥150 GiB.

Model:

```r
design = ~ tissue + treatment + tissue:treatment
```

Test:

- frozen generic infection direction in Feizixiao leaves;
- pathway/signature score;
- fruit transport;
- tissue heterogeneity.

Do not describe this as cultivar-interaction replication.

## Step 7.4 — GSE262200 holdout decision

Before analysis, decide:

- eligible holdout;
- development dataset;
- exploratory only;
- ineligible.

Eligible only if time, SFZ identity/phenotype, biological units, and ID mapping are resolved.

If eligible, test the frozen interaction genes/signature with no reranking.

## Step 7.5 — External pass/fail

For each frozen gene:

- same direction?;
- external q<0.05?;
- |LFC|≥log2(1.5)?;
- CI excludes zero?;
- model/reference/mappability pass?

For each signature/pathway:

- same direction?;
- q<0.05?;
- leading-edge robust?;
- matched-null pass?

## Step 7.6 — Assign external status

Use:

- replicated;
- cross-context supported;
- unsupported;
- contradictory;
- not testable.

Do not hide contradictory results.

## Completion gate

Every frozen discovery has a recorded external outcome, including failures.

---

# Stage 8 — Validate pathways/signatures and optional transcript usage

## Goal

Show that any headline result is not a single-gene artifact and transports across public contexts.

## Step 8.1 — Frozen signature scoring

Apply identical gene membership and weights to:

- PRJNA450886;
- GSE222651;
- GSE262200 if eligible.

Do not re-estimate weights externally.

Compare:

- group score differences;
- effect/CIs;
- direction;
- time trajectory;
- tissue heterogeneity.

## Step 8.2 — Competitive pathway tests

Primary external method:

- camera.

Sensitivity:

- fgseaMultilevel;
- roast.

Use the same gene-set release and mapping rules in every study.

## Step 8.3 — Leading-edge sensitivity

For each supported pathway:

1. remove its largest contributing gene;
2. rerun;
3. require q<0.10;
4. compare against 1,000 matched random sets.

## Step 8.4 — DTU external assessment

Only for frozen DTU events:

- require adequate external transcript abundance;
- test same gene/transcript IDs;
- require same dominant usage direction;
- report annotation/mapping failures.

Because tissues/cultivars differ, use “cross-context DTU support,” not direct replication.

## Completion gate

At least one primary gene signature or pathway passes the frozen multi-study criteria. If none does, the manuscript must emphasize dataset-specific discovery and failed transfer.

---

# Stage 9 — Orthogonal annotation, small-RNA, motif, and literature support

## Goal

Add independent evidence classes without double-counting cohorts or source papers.

## Step 9.1 — High-confidence annotation

For frozen candidates:

- InterPro/Pfam;
- reviewed Swiss-Prot DIAMOND;
- reciprocal orthology/OrthoFinder;
- catalytic residues/full-length model where relevant.

High-confidence function:

- at least two evidence classes;
- ≥70% sequence coverage;
- no conflicting architecture.

Otherwise report family-level function.

## Step 9.2 — Small-RNA coherence

First confirm GSE222650/651 specimen pairing.

Use a separate small-RNA workflow:

- adapter trimming appropriate for small RNA;
- mature-miRNA quantification;
- differential analysis;
- psRNATarget and sPARTA predictions;
- mRNA integration.

Require:

- miRNA q<0.05;
- target mRNA q<0.05;
- opposite direction;
- two target-prediction tools.

Call this orthogonal regulatory coherence, not target validation.

Tools:

- sRNAbench or miRDeep-P2 through Bioconda;
- psRNATarget: [https://www.zhaolab.org/psRNATarget/](https://www.zhaolab.org/psRNATarget/)
- sPARTA: [https://github.com/atulkakrana/sPARTA](https://github.com/atulkakrana/sPARTA)
- PmiREN: [https://www.pmiren.com/](https://www.pmiren.com/)

## Step 9.3 — Promoter motif transport

Discovery:

- AME/STREME on frozen discovery genes;
- 100 matched backgrounds;
- 1-kb/2-kb windows;
- frozen PWMs.

Robust motif criteria:

- q<0.05 in ≥80/100 backgrounds;
- OR≥1.5;
- both windows agree;
- cognate TF family is expressed.

External:

- test frozen PWMs in independently derived external response sets;
- no motif rediscovery or retuning.

Call results candidate motifs only.

Tools:

- MEME Suite: [https://meme-suite.org/](https://meme-suite.org/)
- JASPAR Plants: [https://jaspar.elixir.no/](https://jaspar.elixir.no/)

## Step 9.4 — Published evidence registry

Create:

`results/evidence/published_evidence_registry.tsv`

Fields:

- DOI;
- gene/pathway;
- species/cultivar;
- biological material;
- accession overlap;
- evidence modality;
- independent of current datasets?;
- exact support;
- limitation.

Classify source papers using the same accession as same-data prior interpretation, not validation.

## Completion gate

Orthogonal support is recorded independently from discovery and external dataset support.

---

# Stage 10 — Assign deterministic evidence statuses and candidate tiers

## Goal

Produce reproducible evidence labels with no subjective additive score.

## Step 10.1 — Maintain four separate statuses

For each gene/pathway:

1. discovery;
2. internal robustness;
3. external support;
4. orthogonal support.

Do not collapse them prematurely.

## Step 10.2 — Recommended headline-candidate rule

A headline computational candidate should require:

- discovered at q<0.05 and effect threshold;
- internal robustness pass;
- cross-context support in PRJNA450886;
- no mapping/annotation failure;
- at least one orthogonal evidence class.

Permit zero headline candidates.

## Step 10.3 — Tiers

- **Tier A:** passes all headline rules.
- **Tier B:** discovered and robust, but external support is partial/not testable.
- **Tier C:** pathway/module candidate without gene-level discovery.
- **Exploratory:** post hoc or incomplete.
- **Retired:** contradictory, annotation failure, or mapping bias.

## Step 10.4 — Freeze final evidence matrix

Create:

- `results/candidates/final_evidence_matrix.tsv`
- `results/candidates/final_claims.md`
- `results/candidates/contradictory_results.tsv`

Checksum all final evidence files.

## Completion gate

Every candidate and pathway has traceable, deterministic status and contradictory evidence is visible.

---

# Stage 11 — Produce figures and tables

## Goal

Present discovery, robustness, validation, and orthogonal support as separate evidence layers.

## Main figures

### Figure 1 — Study design and discovery/validation firewall

Panels:

- dataset roles;
- sample designs;
- discovery freeze point;
- external unlock point;
- evidence vocabulary.

### Figure 2 — Discovery-data QC and genome-wide interaction

Panels:

- VST PCA/sample distances;
- mapping/mismatch/coverage;
- interaction MA/volcano;
- Guiwei versus Yurong infection-effect scatter;
- normalized counts for frozen discoveries.

### Figure 3 — Internal robustness

Panels:

- DESeq2 versus edgeR;
- featureCounts versus Salmon;
- filter sensitivity;
- leave-one-out stability;
- mapping-bias flags.

### Figure 4 — External cross-context evaluation

Panels:

- frozen gene forest plots;
- PRJNA450886 24-h primary test;
- 6/48-h temporal behavior;
- GSE222651 tissue transfer;
- GSE262200 outcome if eligible.

Use explicit labels: replicated, cross-context supported, contradictory, not testable.

### Figure 5 — Frozen pathway/signature validation

Panels:

- signature score by study/group;
- pathway NES/effects;
- camera/fgsea/roast concordance;
- leading-edge deletion;
- matched-null results.

### Figure 6 — Conditional secondary discovery

If DTU succeeds:

- transcript-usage interaction;
- isoform proportions;
- external DTU direction;
- mappability/annotation QC.

If DTU fails the gate, omit Figure 6 rather than replacing it post hoc.

### Figure 7 — Orthogonal support

Panels as available:

- annotation evidence;
- small-RNA coherence;
- candidate motif robustness/transport;
- independent published evidence categories.

### Figure 8 — Final evidence matrix

Panels:

- discovery;
- robustness;
- external support;
- orthogonal support;
- final deterministic tier;
- contradictory evidence.

## Main tables

### Table 1 — Dataset role and eligibility

Include:

- accession;
- design;
- source-unit status;
- role;
- estimand;
- eligibility;
- limitation.

### Table 2 — Frozen discovery results

Include:

- gene/pathway;
- interaction effect/SE/P/q;
- effect threshold;
- mappability;
- frozen membership.

### Table 3 — Robustness

Include:

- pipeline results;
- sign;
- LFC difference;
- leave-one-out;
- mapping sensitivity;
- pass/fail.

### Table 4 — External evaluation

Include:

- frozen target;
- dataset/contrast;
- direction;
- effect/CI/q;
- estimand match;
- evidence label.

### Table 5 — Orthogonal support and final status

Include:

- annotation classes;
- small-RNA support;
- motif support;
- independent literature;
- contradiction;
- final tier.

## Supplementary files

- S1 complete metadata/biological-unit registry;
- S2 per-library QC;
- S3 all discovery statistics;
- S4 robustness results;
- S5 all external frozen tests;
- S6 pathway/signature tests;
- S7 DTU results;
- S8 annotation/orthology;
- S9 small-RNA results;
- S10 motif/background tests;
- S11 evidence registry;
- S12 full scripts/environments/commands;
- S13 amendment/deviation log.

## Figure-generation rule

Every figure:

- generated from code;
- writes plotted numeric data;
- shows uncertainty;
- uses frozen IDs/labels;
- includes q values where relevant;
- exports PDF/SVG and journal-required TIFF;
- is conditionally omitted when its gate fails.

---

# Stage 12 — Write the paper in standard bioinformatics-paper structure

## Goal

Write a conventional, coherent bioinformatics paper centered on one new discovery and a clearly separated validation framework.

## 12.1 Title

If the signature transfers externally:

> Genome-wide interaction analysis identifies a robust cultivar-dependent lychee infection-response signature with cross-context support

If external transfer fails:

> Genome-wide interaction reanalysis reveals context-specific lychee responses to *Phytophthora litchii*

Do not commit to the title before external outcomes.

## 12.2 Abstract

Recommended structure:

### Background

- disease importance;
- existing public data;
- missing genome-wide interaction/validation framework.

### Methods

- locked discovery dataset;
- genome-wide interaction;
- internal robustness;
- frozen external testing;
- pathway/signature and optional DTU;
- evidence vocabulary.

### Results

- number/effect of discoveries;
- robustness pass/fail;
- external support/contradiction;
- pathway/signature outcome;
- secondary discovery if gated successfully.

### Conclusions

- exact computational discovery;
- transportability limits;
- no causal-mechanism claim.

## 12.3 Introduction / Background

Suggested paragraphs:

1. lychee economic importance and *P. litchii* disease;
2. resistant/susceptible cultivar biology and prior transcriptomic work;
3. GSE201243 prior use and why selected-gene analysis is insufficient;
4. need for genome-wide interaction and independent evaluation;
5. study hypothesis, discovery/validation firewall, and contributions.

## 12.4 Related Work

Create a distinct section or integrate into the Introduction, depending on journal style.

Cover:

- 2019 Guiwei–Heiye time-course study;
- 2023 LcWRKY/LcCDPK work using GSE201243;
- 2023 Feizixiao mRNA/ncRNA study;
- 2025 lignin/ROS study;
- 2026 LcPIP1/LcWRKY34 work;
- comparable oomycete resistant/susceptible transcriptomics;
- interaction modeling, network preservation, motif enrichment, DTU methods.

State clearly which papers reuse the same accessions.

## 12.5 Materials and Methods

Recommended subsections:

1. study design and evidence definitions;
2. dataset eligibility/provenance;
3. reference resources;
4. raw-read QC and preprocessing;
5. alignment/counting/transcript quantification;
6. discovery interaction model;
7. pathway/signature construction;
8. differential transcript usage;
9. internal robustness analyses;
10. external frozen evaluation;
11. annotation/orthology;
12. small-RNA coherence;
13. promoter motif analysis;
14. published-evidence registry;
15. multiple testing and acceptance criteria;
16. reproducibility/software.

Every model formula, contrast, filter, and multiplicity family must be explicit.

## 12.6 Results

Recommended subsections:

1. provenance and expression QC;
2. genome-wide cultivar×infection discovery;
3. frozen signature/pathways;
4. internal robustness;
5. PRJNA450886 external evaluation;
6. GSE222651 tissue transfer;
7. GSE262200 holdout outcome, if eligible;
8. conditional DTU discovery;
9. orthogonal annotation/small-RNA/motif support;
10. final evidence tiers and contradictory results.

Keep discovery and validation results in separate subsections.

## 12.7 Discussion

Recommended subsections/themes:

1. principal new discovery;
2. which findings are robust versus externally supported;
3. temporal/tissue/cultivar transportability;
4. comparison with related lychee and oomycete studies;
5. interpretation of pathways/signatures;
6. meaning of DTU or orthogonal evidence;
7. contradictory/null results;
8. limitations: source units, sample size, reference bias, context differences, absence of direct replication;
9. practical value of the candidate/signature resource.

Do not equate cross-context support with direct replication.

## 12.8 Conclusion

Use one paragraph:

- discovery;
- validation status;
- claim limits;
- value of the released resource.

## 12.9 Data and Code Availability

List:

- all public accession URLs;
- exact reference releases/checksums;
- code repository;
- archived release DOI;
- count/result tables;
- environment/container;
- amendment log.

## 12.10 Supplementary Information

Provide complete:

- manifests;
- all-gene results;
- robustness;
- external tests;
- orthogonal evidence;
- failed/contradictory results;
- figure source data.

## Writing gate

Before finalizing:

- every sentence labeled internally as discovery, robustness, external, orthogonal, or interpretation;
- no unsupported “validated,” “mechanism,” “functional,” or “resistance gene” language;
- title/abstract match the highest evidence achieved.

---

# Stage 13 — Release data/code and perform final review

## Goal

Make the entire discovery/validation chain auditable.

## Step 13.1 — Workflow release

Release:

- Snakemake workflow;
- pinned environment/container;
- synthetic fixture;
- configs;
- scripts;
- manifests/checksums;
- all result tables;
- figure source data.

## Step 13.2 — Clean reproduction

From a fresh checkout and empty results directory, run the workflow in staged mode rather than retaining all study intermediates:

```bash
micromamba create -n lychee-release \
  -f analysis/envs/lychee-discovery.yml

micromamba activate lychee-release

snakemake \
  --snakefile analysis/workflow/Snakefile \
  --configfile analysis/config/release.yaml \
  --cores 16 \
  --resources alignment_slots=1
```

The release configuration should process one study at a time and run verified cleanup checkpoints between studies. Compare expected hashes for fixture and final numeric outputs.

## Step 13.3 — Independent review

Require:

- statistical review of interaction/FDR/estimands;
- bioinformatics review of reference/quantification;
- independent reproduction of the primary discovery script;
- novelty review against prior accession-linked papers;
- claim-to-evidence audit.

## Step 13.4 — Submission gate

Submit only when:

- discovery freeze predates external outcome analysis;
- external roles did not change after outcomes;
- direct versus cross-context evidence is labeled correctly;
- contradictory results are public;
- all figures regenerate;
- title/abstract obey claim limits;
- code/data links resolve.

---

## Suggested timeline

### Weeks 1–2

- preflight;
- recover/reconstruct assets;
- synthetic tests;
- freeze protocol/dataset roles;
- install/pin tools.

### Weeks 2–6

- acquire/process GSE201243;
- QC/provenance;
- primary discovery;
- freeze genes/pathways/signature/DTU.

### Weeks 5–8

- internal robustness;
- mapping sensitivity;
- finalize discovery status.

### Weeks 8–12

- unlock/process PRJNA450886 and GSE222651;
- decide GSE262200 eligibility;
- run frozen external tests.

### Weeks 11–15

- signature/pathway validation;
- DTU external checks;
- annotation/small-RNA/motif/literature support.

### Weeks 15–18

- final evidence matrix;
- figures/tables;
- manuscript writing;
- clean reproduction and release.

Estimated duration: approximately 4–5 months.

---

## Human decision points

Human approval is required for:

1. discovery hypothesis and fallback;
2. dataset roles/eligibility;
3. GSE262200 holdout decision;
4. sample exclusions;
5. primary pathway collection;
6. novelty gate;
7. final evidence-tier rules;
8. figure/main-versus-supplement selection;
9. manuscript claims/title;
10. journal and final submission.

All download, processing, modeling, robustness, frozen external testing, and scripted figure generation can otherwise be automated.

---

## Immediate next actions

1. Create Stage 0 preflight script and required-input manifest.
2. Recover or reconstruct missing S2/S3/manuscript assets.
3. Write and checksum the prospective retrospective-analysis protocol.
4. Freeze dataset roles and acceptance criteria.
5. Create synthetic interaction fixtures.
6. Install/pin tools and reference releases.
7. Download/checksum GSE201243 only.
8. Verify biological-unit eligibility.
9. Process discovery reads and freeze QC/counts.
10. Run/freeze discovery interaction and pathway signature.
11. Run internal robustness.
12. Unlock external datasets and apply fixed tests.
13. Complete orthogonal support/evidence matrix.
14. Generate figures/tables and write the paper.
15. Release and independently reproduce the workflow.
