# Computational Execution Plan for the Lychee–*Phytophthora litchii* Manuscript

## Purpose and scope

This document converts `docs/lychee_manuscript_improvement_plan.md` into an executable computational workflow.

No new biological samples or laboratory assays are included. The final product is a rigorous public-data reanalysis, integration, and candidate-prioritization resource.

Each stage contains:

- **Goal**
- **What to do**
- **How to do it**
- **Outputs**
- **Completion gate**

## Working paths

```bash
export PROJECT="/Users/rzhuang/Documents/VscodeProjects/lychee"
export ARCHIVE="/Users/rzhuang/Documents/research/lychee"
export RUNROOT="$PROJECT/analysis"
cd "$PROJECT"
```

Commands are templates to run deliberately; they have not yet been executed.

## Stage map

1. Freeze scope and claims
2. Create repository and environments
3. Recover/audit existing assets
4. Acquire metadata and quick-start data
5. Acquire raw reads and references
6. Resolve provenance and freeze manifests
7. Process reads and perform QC
8. Run genome-wide statistical analyses
9. Integrate annotations, pathways, networks, and promoters
10. Freeze computational candidates and robustness results
11. Produce figures and tables
12. Rewrite, release, and submit

---

# Stage 1 — Freeze scope and claims

## Goal

Prevent computational predictions from being presented as biological mechanisms.

## Step 1.1 — Write the claim boundary

Create `analysis/preregistration/computational_scope_v1.md`.

Include:

- public-data-only scope;
- primary GSE201243 interaction;
- primary pathway contrast/collection;
- use of other studies as partial/cross-context evidence;
- q<0.05 interaction criterion;
- no selected-gene-only inference;
- no causal gene, direct regulation, or functional cis-element claims;
- negative-result and fallback rules.

Checksum:

```bash
mkdir -p "$RUNROOT/preregistration"

shasum -a 256 \
  "$RUNROOT/preregistration/computational_scope_v1.md" \
  > "$RUNROOT/preregistration/computational_scope_v1.sha256"
```

## Step 1.2 — Define the final contribution

The target deliverables are:

- raw-read reprocessing;
- genome-wide cultivar×infection inference;
- time/tissue/public-study integration;
- mapping-bias/provenance audit;
- corrected annotation;
- ranked pathways;
- exploratory stable modules;
- robust motif enrichment;
- evidence-ranked candidate resource;
- complete reproducibility package.

## Step 1.3 — Standardize nomenclature

Use:

- *Phytophthora litchii* as current name;
- “syn. *Peronophythora litchii*” at first mention;
- historical names verbatim in titles/metadata;
- `P. litchii` thereafter.

## Completion gate

The title/abstract outline and analysis preregistration contain no mechanistic or causal promises.

---

# Stage 2 — Create repository and environments

## Goal

Establish a versioned, reproducible project before downloading data.

## Step 2.1 — Create directories

```bash
cd "$PROJECT"

mkdir -p \
  analysis/{config,envs,logs,metadata,preregistration,reports,scripts,workflow} \
  data/{raw/fastq,processed,reference/host,reference/pathogen,external} \
  results/{audit,qc,counts,de,interaction,timecourse,meta,annotation,pathways,network,promoters,candidates,figures,tables,supplement} \
  manuscript/{drafts,figures,tables,supplement}

git init
```

Recommended `.gitignore`:

```text
data/raw/
data/processed/
*.bam
*.bai
*.fastq
*.fastq.gz
.snakemake/
analysis/logs/
```

Track metadata, scripts, environments, checksums, small result tables, and documentation.

## Step 2.2 — Install command-line tools

```bash
micromamba create -n lychee-rnaseq -c conda-forge -c bioconda \
  python r-base snakemake-minimal \
  ncbi-datasets-cli sra-tools entrez-direct \
  fastqc multiqc fastp cutadapt \
  star hisat2 salmon subread samtools rseqc picard \
  bedtools gffread seqkit diamond \
  meme aria2 pigz coreutils ripgrep

micromamba activate lychee-rnaseq
```

Install InterProScan/eggNOG-mapper separately at the annotation stage if needed because their databases are large.

## Step 2.3 — Install R packages

```bash
Rscript - <<'RS'
if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", repos = "https://cloud.r-project.org")
}

BiocManager::install(c(
  "DESeq2", "edgeR", "limma", "tximport",
  "apeglm", "IHW", "fgsea", "clusterProfiler",
  "ComplexHeatmap"
), ask = FALSE, update = FALSE)

install.packages(c(
  "tidyverse", "data.table", "patchwork", "ggrepel",
  "pheatmap", "WGCNA", "metafor"
), repos = "https://cloud.r-project.org")
RS
```

Freeze:

```bash
micromamba env export -n lychee-rnaseq \
  > "$RUNROOT/envs/lychee-rnaseq.yml"

Rscript -e 'writeLines(capture.output(sessionInfo()), "'"$RUNROOT"'/envs/R_sessionInfo.txt")'
```

## Step 2.4 — Create workflow configuration

Create `analysis/config/config.yaml` containing:

- project paths;
- accession list;
- reference paths/checksums;
- trimming settings;
- aligner/quantifier;
- strandedness per study;
- count-filter rule;
- release dates.

Create a Snakemake workflow:

`manifest → download → checksum → FastQC → trim → align → count → MultiQC → statistics → figures`

Test:

```bash
snakemake \
  --snakefile analysis/workflow/Snakefile \
  --configfile analysis/config/config.yaml \
  --dry-run
```

## Completion gate

Tools report versions, R packages load, and the workflow dry-run resolves expected targets.

---

# Stage 3 — Recover and audit existing assets

## Goal

Preserve previous work while distinguishing real evidence from templates and exported images.

## Step 3.1 — Import S2 and S3 snapshots

```bash
cd "$PROJECT"

cp "$ARCHIVE/paper/plants/Supplementary_File_S2_reproducible_workflow.zip" \
  analysis/workflow/S2_primary_workflow.zip

cp "$ARCHIVE/paper/plants/supplemental files/Supplementary_File_S3_GSE262200_external_reanalysis_workflow.zip" \
  analysis/workflow/S3_GSE262200_workflow.zip

mkdir -p analysis/workflow/S2 analysis/workflow/S3

unzip -o analysis/workflow/S2_primary_workflow.zip \
  -d analysis/workflow/S2

unzip -o analysis/workflow/S3_GSE262200_workflow.zip \
  -d analysis/workflow/S3

shasum -a 256 analysis/workflow/*.zip \
  > analysis/workflow/archive_checksums.sha256
```

Keep imported snapshots immutable. Modify copies under `analysis/scripts/`.

## Step 3.2 — Inventory local assets

Create `results/audit/local_asset_inventory.tsv`:

`path`, `type`, `role`, `checksum`, `reproducible`, `missing_dependency`, `action`.

Checksum key files:

```bash
shasum -a 256 \
  "$PROJECT/docs/lychee_plants_revised_vixra_format.pdf" \
  "$PROJECT/docs/review_feedback.txt" \
  "$RUNROOT/workflow/"*.zip \
  > "$RUNROOT/metadata/local_asset_checksums.sha256"
```

## Step 3.3 — Audit every current figure/table

Record:

- source data available?;
- script available?;
- reproducible?;
- discrepancy?;
- retain/replace/remove?

Priority:

- 17/117 DEG counts;
- missing genome-wide interaction table;
- metadata PCA;
- exact motif strings/background;
- extreme motif simulation values;
- LITCHI017676/LITCHI019299 annotations;
- descriptive Reactome themes.

Output:

`results/audit/current_claim_reproducibility.tsv`

## Completion gate

Every current claim has a source/evidence status and disposition.

---

# Stage 4 — Acquire metadata and quick-start data

## Goal

Validate analysis code quickly while constructing authoritative metadata.

## Step 4.1 — Download GSE262200 counts

```bash
cd "$PROJECT"

curl -fL --retry 5 \
  -o data/external/GSE262200_readcount.txt.gz \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE262nnn/GSE262200/suppl/GSE262200_readcount.txt.gz"

curl -fL --retry 5 \
  -o data/external/GSE262200_fpkm.txt.gz \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE262nnn/GSE262200/suppl/GSE262200_fpkm.txt.gz"

gzip -t data/external/GSE262200_readcount.txt.gz
gzip -t data/external/GSE262200_fpkm.txt.gz

shasum -a 256 data/external/GSE262200_* \
  > analysis/metadata/GSE262200_checksums.sha256
```

Use only the integer counts for inference.

## Step 4.2 — Download GEO metadata

```bash
curl -fL --retry 5 \
  -o analysis/metadata/GSE201243_family.soft.gz \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE201nnn/GSE201243/soft/GSE201243_family.soft.gz"

curl -fL --retry 5 \
  -o analysis/metadata/GSE222652_family.soft.gz \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE222nnn/GSE222652/soft/GSE222652_family.soft.gz"

curl -fL --retry 5 \
  -o analysis/metadata/GSE262200_family.soft.gz \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE262nnn/GSE262200/soft/GSE262200_family.soft.gz"
```

## Step 4.3 — Generate ENA manifests

```bash
mkdir -p analysis/metadata/ena

for ACC in \
  PRJNA830488 \
  PRJNA450886 \
  PRJNA922966 \
  PRJNA922965 \
  PRJNA1090613
do
  curl -fL --retry 5 \
    "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${ACC}&result=read_run&fields=study_accession,sample_accession,experiment_accession,run_accession,sample_title,experiment_title,scientific_name,library_strategy,library_source,library_selection,library_layout,instrument_model,read_count,base_count,fastq_ftp,fastq_md5&format=tsv" \
    -o "analysis/metadata/ena/${ACC}.tsv"
done

wc -l analysis/metadata/ena/*.tsv
```

Expected data rows:

- PRJNA830488: 12
- PRJNA450886: 36
- PRJNA922966: 12
- PRJNA922965: 12
- PRJNA1090613: 12

Each file also has one header line.

## Step 4.4 — Build provisional master metadata

Implement:

```bash
Rscript analysis/scripts/01_build_master_manifest.R \
  --ena-dir analysis/metadata/ena \
  --geo-dir analysis/metadata \
  --output analysis/metadata/master_samples_provisional.tsv \
  --issues analysis/metadata/metadata_issues.tsv
```

Required columns:

- all accessions;
- sample ID;
- cultivar/genotype;
- resistance label/evidence;
- tissue/time/treatment;
- deposited replicate;
- source-unit provenance;
- isolate/propagule/wounding if known;
- layout/read length/strandedness/instrument;
- FASTQ URL/MD5;
- metadata status.

Never assign conditions from run order alone.

## Completion gate

Expected run counts match, and every missing/conflicting field is recorded.

---

# Stage 5 — Acquire raw reads and references

## Goal

Create checksum-verified, versioned inputs for uniform processing.

## Step 5.1 — Download order

1. PRJNA830488 — primary.
2. PRJNA450886 — time course.
3. PRJNA922966 — tissue validation.
4. PRJNA922965 — optional small RNA.
5. PRJNA1090613 — raw sensitivity after count pilot.

## Step 5.2 — Build URL/checksum lists

Create `analysis/scripts/build_ena_download_lists.py`:

```python
#!/usr/bin/env python3
import csv
from pathlib import Path

manifest_dir = Path("analysis/metadata/ena")
out_dir = Path("analysis/metadata/downloads")
out_dir.mkdir(parents=True, exist_ok=True)

urls = []
checksums = []

for manifest in sorted(manifest_dir.glob("*.tsv")):
    study = manifest.stem
    with manifest.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            fastq_urls = [x for x in row["fastq_ftp"].split(";") if x]
            fastq_md5s = [x for x in row["fastq_md5"].split(";") if x]
            if len(fastq_urls) != len(fastq_md5s):
                raise ValueError(f"URL/MD5 mismatch: {row['run_accession']}")
            for url, checksum in zip(fastq_urls, fastq_md5s):
                url = url if url.startswith("http") else f"https://{url}"
                filename = Path(url).name
                urls.append((study, row["run_accession"], url, filename))
                checksums.append((study, row["run_accession"], checksum, filename))

with (out_dir / "fastq_urls.tsv").open("w") as handle:
    for row in urls:
        handle.write("\t".join(row) + "\n")

with (out_dir / "fastq_md5.tsv").open("w") as handle:
    for row in checksums:
        handle.write("\t".join(row) + "\n")
```

Run:

```bash
python analysis/scripts/build_ena_download_lists.py
```

## Step 5.3 — Download one study

```bash
STUDY="PRJNA830488"
mkdir -p "data/raw/fastq/$STUDY"

awk -F $'\t' -v s="$STUDY" '$1 == s {print $3}' \
  analysis/metadata/downloads/fastq_urls.tsv \
  > "analysis/metadata/downloads/${STUDY}_urls.txt"

aria2c \
  --continue=true \
  --max-connection-per-server=2 \
  --split=2 \
  --input-file="analysis/metadata/downloads/${STUDY}_urls.txt" \
  --dir="data/raw/fastq/$STUDY"
```

## Step 5.4 — Verify MD5

Create `analysis/scripts/verify_ena_md5.py`:

```python
#!/usr/bin/env python3
import csv
import hashlib
import sys
from pathlib import Path

study = sys.argv[1]
root = Path(sys.argv[2])
manifest = Path("analysis/metadata/downloads/fastq_md5.tsv")

expected = {}
with manifest.open() as handle:
    for row in csv.reader(handle, delimiter="\t"):
        if row[0] == study:
            expected[row[3]] = row[2]

failed = []
for filename, wanted in sorted(expected.items()):
    path = root / filename
    if not path.exists():
        failed.append((filename, "MISSING"))
        continue
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != wanted:
        failed.append((filename, digest.hexdigest()))

if failed:
    for item in failed:
        print("\t".join(item))
    raise SystemExit(1)

print(f"{study}: verified {len(expected)} files")
```

Run:

```bash
python analysis/scripts/verify_ena_md5.py \
  PRJNA830488 data/raw/fastq/PRJNA830488
```

## Step 5.5 — Download host reference

```bash
datasets download genome accession GCA_019925255.1 \
  --include genome,seq-report \
  --filename data/reference/host/GCA_019925255.1.zip

unzip -o data/reference/host/GCA_019925255.1.zip \
  -d data/reference/host/GCA_019925255.1
```

Matching external gene models:

```bash
cd "$PROJECT/data/reference/host"

curl -fL --retry 5 \
  -o Lchinesis_genome.Chr.fasta.gz \
  "http://www.sapindaceae.com/file_download/Lchinesis_genome.Chr.fasta.gz"

curl -fL --retry 5 \
  -o Lchinesis_genome.Chr.gff3.gz \
  "http://www.sapindaceae.com/file_download/Lchinesis_genome.Chr.gff3.gz"

curl -fL --retry 5 \
  -o Lchinesis_genome.sim.cds.fa.gz \
  "http://www.sapindaceae.com/file_download/Lchinesis_genome.sim.cds.fa.gz"

curl -fL --retry 5 \
  -o Lchinesis_genome.pep.sim.fa.gz \
  "http://www.sapindaceae.com/file_download/Lchinesis_genome.pep.sim.fa.gz"

gzip -t ./*.gz
shasum -a 256 ./*.gz > host_reference_checksums.sha256

gzip -dc Lchinesis_genome.Chr.fasta.gz > Lchinesis_genome.Chr.fasta
gzip -dc Lchinesis_genome.Chr.gff3.gz > Lchinesis_genome.Chr.gff3
```

Validate FASTA/GFF chromosome compatibility before analysis.

## Step 5.6 — Download pathogen mapping sequence

```bash
cd "$PROJECT/data/reference/pathogen"

curl -fL --retry 5 \
  -o GWHAOTU00000000.genome.fasta.gz \
  "https://download.cncb.ac.cn/gwh/Protists/Phytophthora_litchii_Phytophthora_litchii_GWHAOTU00000000/GWHAOTU00000000.genome.fasta.gz"

curl -fL --retry 5 \
  -o GWHAOTU00000000_md5.txt \
  "https://download.cncb.ac.cn/gwh/Protists/Phytophthora_litchii_Phytophthora_litchii_GWHAOTU00000000/GWHAOTU00000000_md5.txt"

gzip -t GWHAOTU00000000.genome.fasta.gz
```

Use the genome for competitive mapping. Add versioned pathogen annotation only if it can be acquired and checksummed reproducibly.

## Step 5.7 — Build combined reference

```bash
cd "$PROJECT"
mkdir -p data/reference/combined/star_index

gzip -dc data/reference/host/Lchinesis_genome.Chr.fasta.gz \
  | sed '/^>/ s/^>/HOST_/' \
  > data/reference/combined/host.fa

gzip -dc data/reference/pathogen/GWHAOTU00000000.genome.fasta.gz \
  | sed '/^>/ s/^>/PATH_/' \
  > data/reference/combined/pathogen.fa

cat data/reference/combined/host.fa \
    data/reference/combined/pathogen.fa \
  > data/reference/combined/lychee_pathogen.fa

awk 'BEGIN{OFS="\t"} /^#/ {print; next} {$1="HOST_" $1; print}' \
  data/reference/host/Lchinesis_genome.Chr.gff3 \
  > data/reference/host/host_annotation.prefixed.gff3

gffread data/reference/host/host_annotation.prefixed.gff3 \
  -T \
  -o data/reference/host/host_annotation.prefixed.gtf

STAR --runMode genomeGenerate \
  --runThreadN 8 \
  --genomeDir data/reference/combined/star_index \
  --genomeFastaFiles data/reference/combined/lychee_pathogen.fa \
  --sjdbGTFfile data/reference/host/host_annotation.prefixed.gtf \
  --sjdbOverhang 149
```

## Completion gate

Primary FASTQ pass MD5, reference compatibility is documented, and the combined index builds.

---

# Stage 6 — Resolve provenance and freeze manifests

## Goal

Make every uncertainty explicit before inference.

## Step 6.1 — Reconcile sources

Compare:

- GEO/GSM;
- SRA/ENA/BioSample;
- associated methods;
- supplementary metadata.

Resolve or flag:

- GSE201243 instrument/method conflicts;
- source-tree independence;
- PRJNA450886 fruit-pool provenance;
- GSE222650/651 sample pairing;
- GSE262200 time/SFZ identity/phenotype.

## Step 6.2 — Contact submitters

Ask only for missing fields necessary for interpretation. Archive correspondence under `analysis/metadata/correspondence/`.

## Step 6.3 — Freeze manifest

```bash
Rscript analysis/scripts/02_validate_and_freeze_manifest.R \
  --input analysis/metadata/master_samples_provisional.tsv \
  --output analysis/metadata/master_samples_v1.tsv \
  --issues analysis/metadata/unresolved_metadata_v1.tsv

shasum -a 256 analysis/metadata/master_samples_v1.tsv \
  > analysis/metadata/master_samples_v1.sha256
```

Reject duplicate runs, missing required analysis fields, unexpected group sizes, and inconsistent condition labels.

## Completion gate

The manifest is versioned; unresolved provenance limits are carried into analysis labels and manuscript claims.

---

# Stage 7 — Process reads and perform QC

## Goal

Generate one reproducible count matrix per study and determine whether libraries support inference.

## Step 7.1 — Two-sample smoke test

Run one pair of contrasting PRJNA830488 libraries through:

- FastQC;
- fastp;
- STAR;
- samtools;
- featureCounts;
- RSeQC;
- MultiQC.

Confirm paired mates, GTF/index compatibility, nonempty `LITCHI` counts, disk use, and runtime.

## Step 7.2 — Raw QC

```bash
mkdir -p results/qc/raw_fastqc results/qc/raw_multiqc

rg --files data/raw/fastq -g "*.fastq.gz" \
  | xargs -n 1 -P 4 fastqc \
      --threads 2 \
      --outdir results/qc/raw_fastqc

multiqc results/qc/raw_fastqc \
  --outdir results/qc/raw_multiqc
```

Review quality, adapters, length, duplication, overrepresented sequences, and depth. Do not exclude by warning color alone.

## Step 7.3 — Trim

Example:

```bash
RUN="SRR18856600"
STUDY="PRJNA830488"

mkdir -p "data/processed/trimmed/$STUDY" \
         "analysis/logs/fastp/$STUDY"

fastp \
  --in1 "data/raw/fastq/$STUDY/${RUN}_1.fastq.gz" \
  --in2 "data/raw/fastq/$STUDY/${RUN}_2.fastq.gz" \
  --out1 "data/processed/trimmed/$STUDY/${RUN}_1.trim.fastq.gz" \
  --out2 "data/processed/trimmed/$STUDY/${RUN}_2.trim.fastq.gz" \
  --thread 8 \
  --detect_adapter_for_pe \
  --html "analysis/logs/fastp/$STUDY/${RUN}.html" \
  --json "analysis/logs/fastp/$STUDY/${RUN}.json"
```

Implement as a manifest-driven Snakemake rule.

## Step 7.4 — Align

```bash
RUN="SRR18856600"
STUDY="PRJNA830488"

mkdir -p "data/processed/aligned/$STUDY/$RUN"

STAR \
  --runThreadN 12 \
  --genomeDir data/reference/combined/star_index \
  --readFilesIn \
    "data/processed/trimmed/$STUDY/${RUN}_1.trim.fastq.gz" \
    "data/processed/trimmed/$STUDY/${RUN}_2.trim.fastq.gz" \
  --readFilesCommand zcat \
  --outFileNamePrefix "data/processed/aligned/$STUDY/$RUN/" \
  --outSAMtype BAM SortedByCoordinate \
  --quantMode GeneCounts \
  --outFilterMultimapNmax 20

samtools index \
  "data/processed/aligned/$STUDY/$RUN/Aligned.sortedByCoord.out.bam"
```

Record unique/multiple mapping, mismatches, and host/pathogen fractions.

## Step 7.5 — Infer strandedness

```bash
infer_experiment.py \
  -r data/reference/host/host_annotation.prefixed.bed12 \
  -i data/processed/aligned/PRJNA830488/SRR18856600/Aligned.sortedByCoord.out.bam \
  > results/qc/PRJNA830488_strandedness.txt
```

Test several libraries per study. Freeze the featureCounts `-s` value.

## Step 7.6 — Count genes

```bash
featureCounts \
  -T 12 \
  -p \
  --countReadPairs \
  -s 0 \
  -t exon \
  -g gene_id \
  -a data/reference/host/host_annotation.prefixed.gtf \
  -o results/counts/PRJNA830488_featureCounts.txt \
  $(cat analysis/metadata/PRJNA830488_bam_paths.txt)
```

Replace `-s 0` with empirical strandedness.

Clean matrix:

```bash
Rscript analysis/scripts/03_clean_featurecounts.R \
  --input results/counts/PRJNA830488_featureCounts.txt \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --study PRJNA830488 \
  --output results/counts/PRJNA830488_counts.tsv
```

## Step 7.7 — Salmon sensitivity

```bash
gffread data/reference/host/Lchinesis_genome.Chr.gff3 \
  -g data/reference/host/Lchinesis_genome.Chr.fasta \
  -w data/reference/host/Lchinesis_genome.transcripts.fa

salmon index \
  -t data/reference/host/Lchinesis_genome.transcripts.fa \
  -i data/reference/host/salmon_index \
  -k 31

salmon quant \
  -i data/reference/host/salmon_index \
  -l A \
  -1 data/processed/trimmed/PRJNA830488/SRR18856600_1.trim.fastq.gz \
  -2 data/processed/trimmed/PRJNA830488/SRR18856600_2.trim.fastq.gz \
  --validateMappings \
  --gcBias \
  --seqBias \
  -p 8 \
  -o data/processed/salmon/PRJNA830488/SRR18856600
```

Summarize with tximport using a transcript-to-gene map from the same annotation.

## Step 7.8 — Consolidate QC

```bash
multiqc \
  results/qc \
  analysis/logs/fastp \
  data/processed/aligned \
  data/processed/salmon \
  --outdir results/qc/final_multiqc
```

Produce:

- library QC table;
- per-study VST PCA;
- sample distances;
- replicate correlations;
- detected genes;
- Cook’s distance;
- mapping bias by cultivar;
- pathogen-read fraction.

Exclude only for documented technical/label failure or multiple concordant QC failures. Preserve with/without-exclusion results.

## Completion gate

Expected sample counts, no technical confounding, documented mapping bias, and real expression QC.

---

# Stage 8 — Run genome-wide statistical analyses

## Goal

Produce complete all-gene inferential results before candidate ranking.

## Step 8.1 — GSE262200 quick analysis

```bash
Rscript analysis/scripts/10_gse262200_interaction.R \
  --counts data/external/GSE262200_readcount.txt.gz \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --outdir results/de/GSE262200
```

Model:

```r
design = ~ genotype + treatment + genotype:treatment
```

Do not infer SFZ phenotype or time.

## Step 8.2 — Primary GSE201243 interaction

```bash
Rscript analysis/scripts/11_gse201243_interaction.R \
  --counts results/counts/PRJNA830488_counts.tsv \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --outdir results/interaction/GSE201243
```

Model:

```r
design = ~ cultivar + treatment + cultivar:treatment
```

Run:

- Wald interaction;
- full/reduced LRT;
- within-cultivar infection;
- LFC shrinkage for display;
- leave-one-library-out;
- featureCounts/Salmon sensitivity.

Required files:

- all-gene interaction;
- both within-cultivar results;
- q<0.05 interactions;
- leave-one-out;
- old-18 audit.

No q<0.05 interactions is a valid result.

## Step 8.3 — PRJNA450886 time course

```bash
Rscript analysis/scripts/12_prjna450886_timecourse.R \
  --counts results/counts/PRJNA450886_counts.tsv \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --outdir results/timecourse/PRJNA450886
```

Model:

```r
design = ~ cultivar * treatment * time
```

Tests:

- three-way LRT;
- infection within cultivar/time;
- interaction at each time;
- interaction changes;
- edgeR/limma sensitivity.

Label as cross-context if source-unit provenance is unresolved.

## Step 8.4 — PRJNA922966 tissue analysis

```bash
Rscript analysis/scripts/13_prjna922966_tissue.R \
  --counts results/counts/PRJNA922966_counts.tsv \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --outdir results/de/PRJNA922966
```

Model:

```r
design = ~ tissue + treatment + tissue:treatment
```

## Step 8.5 — Required reporting

For each model:

- filter;
- tested genes;
- model matrix/coefficient names;
- base mean;
- effect/SE/statistic/P/q;
- all normalized counts for plotted genes;
- session info;
- diagnostics and sensitivity.

## Completion gate

Every study has complete all-gene tables. No final candidate ranking has yet occurred.

---

# Stage 9 — Integrate annotations, pathways, networks, and promoters

## Goal

Create an evidence-ranked computational resource without implying causality.

## Step 9.1 — Cross-study integration

```bash
Rscript analysis/scripts/20_cross_study_integration.R \
  --gse201243 results/interaction/GSE201243 \
  --prjna450886 results/timecourse/PRJNA450886 \
  --prjna922966 results/de/PRJNA922966 \
  --gse262200 results/de/GSE262200 \
  --outdir results/meta
```

Classify:

- direct;
- partial;
- pathway-level;
- not replicated;
- not testable.

Use meta-analysis only for comparable effects and report heterogeneity.

## Step 9.2 — Annotation

```bash
diamond makedb \
  --in data/reference/annotation/swissprot_plants.fasta \
  --db data/reference/annotation/swissprot_plants

diamond blastp \
  --query data/reference/host/Lchinesis_genome.pep.sim.fa.gz \
  --db data/reference/annotation/swissprot_plants \
  --out results/annotation/lychee_swissprot.tsv \
  --outfmt 6 qseqid sseqid pident length qlen slen evalue bitscore \
  --sensitive \
  --max-target-seqs 10 \
  --evalue 1e-5 \
  --threads 12
```

Also run:

- InterPro/Pfam;
- eggNOG-mapper;
- TAIR12/named-rice orthology;
- reciprocal-best-hit/OrthoFinder;
- TF classification.

Outputs:

- all-gene annotation;
- corrected old-18 table;
- TF catalog;
- orthology map.

## Step 9.3 — Ranked pathways

```bash
Rscript analysis/scripts/21_ranked_pathways.R \
  --stats results/interaction/GSE201243/all_genes_interaction.tsv \
  --orthology results/annotation/orthology_map.tsv \
  --genesets analysis/config/genesets \
  --outdir results/pathways/GSE201243
```

Use:

- prespecified primary collection/contrast;
- fgsea/camera;
- hierarchical/global FDR;
- expressed-gene ORA background;
- one-to-many orthology control;
- leading-edge genes.

## Step 9.4 — Exploratory network

```bash
Rscript analysis/scripts/22_prjna450886_network.R \
  --vst results/timecourse/PRJNA450886/vst_expression.tsv \
  --manifest analysis/metadata/master_samples_v1.tsv \
  --outdir results/network/PRJNA450886
```

Requirements:

- signed robust network;
- data-driven threshold;
- ≥30-gene modules;
- source-unit-aware bootstrap;
- factorial eigengene tests;
- condition sensitivity;
- preservation/module-score checks.

Remove from the main paper if unstable.

## Step 9.5 — Extract promoters

```bash
Rscript analysis/scripts/23_build_promoter_bed.R \
  --gff data/reference/host/Lchinesis_genome.Chr.gff3 \
  --genome data/reference/host/Lchinesis_genome.Chr.fasta \
  --upstream 2000 \
  --downstream 200 \
  --output results/promoters/all_promoters.bed

bedtools getfasta \
  -s \
  -name \
  -fi data/reference/host/Lchinesis_genome.Chr.fasta \
  -bed results/promoters/all_promoters.bed \
  -fo results/promoters/all_promoters.fa
```

Mark boundaries/overlaps and whether coordinates represent TSS, gene start, or CDS start.

## Step 9.6 — Motif enrichment

```bash
ame \
  --oc results/promoters/ame_primary \
  --control results/promoters/matched_background.fa \
  results/promoters/primary_gene_set.fa \
  data/reference/motifs/JASPAR2026_plants.meme

streme \
  --p results/promoters/primary_gene_set.fa \
  --n results/promoters/matched_background.fa \
  --oc results/promoters/streme_primary

tomtom \
  -oc results/promoters/tomtom_primary \
  results/promoters/streme_primary/streme.txt \
  data/reference/motifs/JASPAR2026_plants.meme
```

Repeat matched backgrounds and promoter windows. Apply motif FDR. Call motifs candidates only.

## Completion gate

Cross-study, annotation, pathway, network, and motif outputs are complete with limitations and sensitivity results.

---

# Stage 10 — Freeze computational candidates and robustness results

## Goal

Produce a transparent evidence ranking rather than a post hoc “top gene” list.

## Step 10.1 — Build evidence matrix

Create:

`results/candidates/candidate_evidence_matrix.tsv`

Columns:

- gene/transcript;
- annotation confidence;
- interaction q/effect;
- within-cultivar effects;
- leave-one-out stability;
- quantifier/filter sensitivity;
- temporal evidence;
- tissue evidence;
- GSE262200 consistency;
- pathway/module;
- motif/TF-family coherence;
- mapping-bias risk;
- novelty;
- final tier;
- decision reason.

## Step 10.2 — Assign evidence tiers

- **Tier A:** statistically supported and stable with cross-context support.
- **Tier B:** stable pathway/time evidence but weaker gene-level interaction.
- **Tier C:** exploratory, context-specific, or poorly annotated.
- **Retired:** annotation/model/statistical failure.

No tier is “validated resistance gene.”

## Step 10.3 — Run robustness matrix

For leading candidates compare:

- featureCounts versus Salmon;
- primary versus alternate filter;
- with/without justified outliers;
- leave-one-library-out;
- alternate promoter windows/background draws;
- alternate orthology rules;
- cross-study sign/heterogeneity.

Output:

`results/candidates/candidate_robustness.tsv`

## Step 10.4 — Freeze interpretation

Create:

`analysis/preregistration/final_computational_interpretation_v1.md`

Record:

- primary findings;
- null findings;
- evidence tiers;
- claims allowed;
- claims prohibited;
- main-paper versus supplement decisions.

Checksum:

```bash
shasum -a 256 \
  analysis/preregistration/final_computational_interpretation_v1.md \
  > analysis/preregistration/final_computational_interpretation_v1.sha256
```

## Completion gate

Candidate ranking is fully traceable and unchanged during manuscript drafting except for documented error correction.

---

# Stage 11 — Produce figures and tables

## Goal

Generate every final output from scripts and frozen numeric tables.

## Step 11.1 — Main figures

1. Designs, provenance, and expression QC.
2. Genome-wide GSE201243 interaction.
3. Time-course and cross-study consistency.
4. Ranked pathway results.
5. Exploratory stable modules/candidates.
6. Robust promoter motif enrichment.
7. Final evidence-ranked candidate resource.

## Step 11.2 — Main tables

1. Dataset inventory/provenance.
2. Leading genome-wide interactions.
3. Cross-study effects/heterogeneity.
4. Pathway results.
5. Candidate evidence matrix.

## Step 11.3 — Supplement

- complete metadata/checksums/conflicts;
- per-library QC;
- all DE/interactions;
- transcript/gene/unigene map;
- annotation/orthology;
- all pathway tests;
- network membership/bootstrap;
- motif results/sites;
- candidate matrix;
- software/commands;
- model diagnostics/sensitivities.

## Step 11.4 — Script outputs

```bash
Rscript analysis/scripts/30_figure_1_qc.R
Rscript analysis/scripts/31_figure_2_interaction.R
Rscript analysis/scripts/32_figure_3_cross_study.R
Rscript analysis/scripts/33_figure_4_pathways.R
Rscript analysis/scripts/34_figure_5_network.R
Rscript analysis/scripts/35_figure_6_motifs.R
Rscript analysis/scripts/36_figure_7_candidates.R
Rscript analysis/scripts/40_main_tables.R
Rscript analysis/scripts/41_supplement.R
```

Each script must:

- read frozen tables;
- write plot data;
- include uncertainty/q values;
- use consistent IDs/colors;
- export PDF/SVG and required TIFF;
- record session info;
- avoid manual numeric edits.

## Step 11.5 — Remove obsolete outputs

Remove/demote:

- metadata PCA;
- selected-gene chromosome plot;
- unrelated structures/protein motifs;
- raw PlantCARE counts;
- descriptive Reactome theme table.

## Completion gate

A clean workflow run regenerates every final figure and table.

---

# Stage 12 — Rewrite, release, and submit

## Goal

Produce an evidence-calibrated reanalysis/resource paper with a complete reproducibility package.

## Step 12.1 — Rewrite structure

### Introduction

1. disease/taxonomy;
2. prior cultivar studies;
3. prior use of GSE201243;
4. statistical/reproducibility gap;
5. computational aims/limits.

### Results

1. provenance and QC;
2. genome-wide interaction;
3. time-course;
4. tissue/additional genotype;
5. cross-study integration;
6. annotation/pathways;
7. exploratory network/motifs;
8. candidate resource.

### Discussion

- principal statistically supported result;
- time/context dependence;
- agreement/disagreement with prior work;
- pathway interpretation;
- why DEG count is not defense strength;
- candidate value and uncertainty;
- provenance/reference/sample-size limits;
- unresolved causal questions outside the public-data scope.

## Step 12.2 — Use a computational title

Example:

> Genome-wide interaction and cross-study transcriptomic reanalysis prioritize cultivar-dependent lychee responses to *Phytophthora litchii*

Avoid “mechanism,” “regulatory architecture,” “functional cis-elements,” and “resistance genes.”

## Step 12.3 — Build release package

Release:

- manifests/checksums;
- counts;
- all-gene statistical results;
- annotation/orthology;
- pathways/networks/motifs;
- candidate matrix;
- plotted data;
- scripts/workflow;
- environments;
- README/data dictionary.

Add S3 and the complete workflow to the versioned repository/Zenodo release.

## Step 12.4 — Reproduce cleanly

```bash
micromamba create -n lychee-release \
  -f analysis/envs/lychee-rnaseq.yml

micromamba activate lychee-release

snakemake \
  --snakefile analysis/workflow/Snakefile \
  --configfile analysis/config/release.yaml \
  --cores 24 \
  --rerun-incomplete
```

Compare final numeric-table and plot-data checksums.

## Step 12.5 — Internal review

Obtain:

- statistical review of formulas/FDR;
- bioinformatics review of mapping/annotation;
- independent reproduction of the primary interaction;
- nomenclature/format review;
- final claim-to-evidence audit.

## Step 12.6 — Submission gate

Submit only when:

- every claim maps to an output;
- all figures are scripted;
- full interaction tables are public;
- provenance limits are explicit;
- title/abstract do not overclaim;
- code/data links resolve.

---

## Execution schedule

### Weeks 1–2

- repository/environment;
- import S2/S3;
- GSE262200 counts;
- ENA/GEO manifests;
- provisional metadata;
- quick interaction script.

### Weeks 2–6

- download/check GSE201243;
- freeze references;
- raw processing/QC;
- genome-wide interaction;
- old-18 audit.

### Weeks 5–10

- PRJNA450886 processing/time course;
- GSE222651 processing/tissue analysis;
- optional small RNA;
- all-gene result release candidates.

### Weeks 9–14

- corrected annotation/orthology;
- cross-study integration;
- pathways;
- exploratory network;
- promoter motifs;
- evidence matrix.

### Weeks 13–18

- robustness;
- figures/tables;
- manuscript rewrite;
- clean reproduction;
- release/internal review.

Estimated duration: approximately 4–5 months, depending on download speed, compute, metadata clarification, and annotation setup.

---

## Immediate commands/actions

1. Create repository structure and environment.
2. Import/checksum S2 and S3.
3. Download GSE262200 counts.
4. Generate ENA manifests.
5. Build/freeze metadata.
6. Download/check GSE201243 FASTQ.
7. Validate host FASTA/GFF.
8. Process GSE201243 and run expression QC.
9. Run genome-wide interaction.
10. Process PRJNA450886 and GSE222651.
11. Complete integration/annotation/pathways/network/motifs.
12. Freeze evidence tiers.
13. Script figures/tables.
14. Rewrite and release.
