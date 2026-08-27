# Lychee discovery/validation reanalysis

This repository implements the staged computational discovery and validation
workflow in `docs/lychee_revised_discovery_validation_plan.md`.

The analysis firewall is operational:

- GSE201243 / PRJNA830488 is the only discovery dataset.
- External biological outcomes remain unopened until discovery artifacts are
  frozen and checksummed.
- PRJNA450886 is the primary cross-context evaluation.
- GSE222651 is a tissue/cultivar transfer study, not direct replication.
- GSE222650 is an orthogonal small-RNA cohort paired with GSE222651.
- GSE262200 is exploratory because public metadata do not resolve sampling time,
  SFZ resistance phenotype, or source-unit independence.

Current status and gate results are written under `results/audit/`. Run the
small, outcome-free validation layer with:

```bash
python3 analysis/scripts/00_preflight.py \
  --project . \
  --required analysis/config/required_inputs.yaml \
  --report results/audit/preflight_report.tsv

Rscript analysis/tests/create_synthetic_fixture.R \
  --seed 20260718 \
  --outdir analysis/tests/fixtures

Rscript analysis/tests/test_interaction_pipeline.R \
  --fixture analysis/tests/fixtures \
  --expected analysis/tests/fixtures/expected_results.tsv
```

The full workflow is defined in `analysis/workflow/Snakefile`. It is configured
for one alignment at a time because the host has 16 CPUs but only about 15 GiB
RAM. Large FASTQ and alignment intermediates are deliberately ignored; manifests,
checksums, frozen matrices, statistics, and audit reports are retained.

## Staged production run

Create the pinned environment and execute discovery first:

```bash
.tools/bin/micromamba create -p .conda/lychee-discovery \
  -f analysis/envs/lychee-discovery.yml

.tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
  --snakefile analysis/workflow/Snakefile \
  --configfile analysis/config/release.yaml \
  --cores 16 \
  --resources mem_mb=15000 alignment_slots=1 \
  --rerun-triggers mtime --printshellcmds
```

`Snakefile` freezes and hashes the discovery result before writing the external
outcome-unlock timestamp. Do not inspect external expression outcomes before
`results/discovery/frozen_results.sha256` verifies and the unlock file exists.

Run each external study separately, in this fixed order:

```bash
for study in PRJNA450886 PRJNA922966 PRJNA1090613; do
  .tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
    --snakefile analysis/workflow/external_study.smk \
    --configfile analysis/config/release.yaml \
    --config study="${study}" \
    --cores 16 \
    --resources mem_mb=15000 alignment_slots=1 download_slots=1 \
    --rerun-triggers mtime --printshellcmds
done
```

The loop above is concise, but on space-constrained hosts invoke the studies one
at a time and run `analysis/scripts/22_cleanup_study.py` after verifying that
study's matrix, technical-QC report, and external-results manifest. The cleanup
is fail-closed, restricted to the frozen study registry, re-verifies every raw
FASTQ against its retained ENA MD5 immediately before deletion, and records all
removed raw/trimmed/alignment bytes in `analysis/logs/storage_cleanup.tsv`.

After all external stages finish, generate the integrated evidence, figures,
tables, manuscript, and release audit:

```bash
.tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
  --snakefile analysis/workflow/finalize.smk \
  --configfile analysis/config/release.yaml \
  --cores 16 --resources mem_mb=15000 \
  --rerun-triggers mtime --printshellcmds
```

The release audit intentionally leaves the statistical review, bioinformatics
review, independent reproduction, novelty review, claim-to-evidence review, and
submission approval as human/owner gates. Automated success must not be
reported as satisfying those gates.

## Regression tests

Run all outcome-free Python tests with:

```bash
python3 -m unittest discover -s analysis/tests -p 'test_*.py'
```

R regression tests are individual executable scripts under `analysis/tests/`.
The reporting smoke test builds a production-shaped temporary result tree and
also checks the PDF and DOCX manuscript exports when LibreOffice is available.
