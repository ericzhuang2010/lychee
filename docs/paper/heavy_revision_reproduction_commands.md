# Heavy-machine revision reproduction commands

Run from the repository root in the pinned `.conda/lychee-discovery` environment.
The NCBI search in H8 was run against the live service on 2026-08-27; script 40
materializes that retrospective query record and does not claim to replay the
unrecorded historical search.

## H1 and H2

```bash
.conda/lychee-discovery/bin/Rscript analysis/scripts/39_revision_heavy_statistics.R \
  --counts results/quantification/PRJNA830488/gene_counts.tsv \
  --metadata analysis/metadata/PRJNA830488_samples.tsv \
  --decisions results/audit/PRJNA830488_sample_decisions.tsv \
  --config analysis/config/discovery.yaml \
  --legacy analysis/config/legacy_18.tsv \
  --s3 results/supplement/S3_all_discovery_statistics.tsv \
  --robustness results/tables/Table3_internal_robustness.tsv \
  --supplement_out results/supplement/S14_legacy_within_cultivar_audit.tsv \
  --sensitivity_out results/revision/H2_composite_null_all_genes.tsv \
  --summary_out results/revision/H2_composite_null_summary.tsv \
  --workdir results/revision/H1_H2
```

## H4 and H6

```bash
.conda/lychee-discovery/bin/python analysis/scripts/35_generate_figures_tables.py \
  --root . --revision-only
.conda/lychee-discovery/bin/python docs/paper/unified_manuscript/build_figures.py
```

## H8 and H9

```bash
.conda/lychee-discovery/bin/python analysis/scripts/40_revision_documentation.py --root .
```

## H5

```bash
.conda/lychee-discovery/bin/python analysis/scripts/41_controlled_motif_background.py \
  --legacy analysis/config/legacy_18.tsv \
  --promoter-metadata results/evidence/motifs/inputs/promoter_metadata.tsv \
  --genome data/reference/combined/host_pathogen.fa \
  --config analysis/config/orthogonal_validation.yaml \
  --outdir results/revision/H5_controlled_motif \
  --supplement results/supplement/S15_controlled_motif_background.tsv \
  --random-sets 100000 --chunk-size 500
```

## H3

```bash
.conda/lychee-discovery/bin/Rscript analysis/scripts/42_simulation_power_analysis.R \
  --discovery-counts results/quantification/PRJNA830488/gene_counts.tsv \
  --discovery-metadata analysis/metadata/PRJNA830488_samples.tsv \
  --discovery-decisions results/audit/PRJNA830488_sample_decisions.tsv \
  --external-counts results/quantification/PRJNA450886/gene_counts.tsv \
  --external-metadata analysis/metadata/PRJNA450886_samples.tsv \
  --external-decisions results/audit/PRJNA450886_sample_decisions.tsv \
  --frozen-genes results/discovery/frozen_genes.tsv \
  --outdir results/revision/H3_power \
  --figure-prefix results/figures/FigureS2_power_analysis \
  --source-data results/figures/source_data/FigureS2_power_analysis_source_data.tsv \
  --supplement results/supplement/S18_power_simulation_mde.tsv \
  --iterations 100 --grid 0,0.5,0.75,1,1.25,1.5,1.75,2,2.5,3,3.5,4
```

The implementation is sequential and vectorized over genes. This keeps peak
memory below 1 GB on the observed run; the tradeoff is approximately 1.5–2
hours of wall time for 1,200 simulations.

## H7 and manuscript integration

```bash
.conda/lychee-discovery/bin/python docs/paper/unified_manuscript/build_figures.py
.conda/lychee-discovery/bin/python analysis/scripts/43_integrate_heavy_revision.py --root .
```

The viXra-format integration additionally requires a headless LibreOffice UNO
listener on port 2002:

```bash
/usr/bin/python3 analysis/scripts/38_integrate_vixra_manuscript.py \
  --template docs/paper/lychee_plants_revised_vixra_format.docx \
  --manuscript docs/paper/unified_manuscript/manuscript.md \
  --output docs/paper/lychee_plants_revised_vixra_format_integrated.docx \
  --port 2002
```

## H10 release and final audit

```bash
.conda/lychee-discovery/bin/python analysis/scripts/44_build_doi_release.py \
  --root . --date 2026-08-27
.conda/lychee-discovery/bin/python analysis/scripts/45_validate_revision_deliverables.py \
  --root . --date 2026-08-27
```

Zenodo sign-in, DOI reservation, metadata approval, and publication remain
author-authenticated actions; see `docs/paper/zenodo_release_checklist.md`.

