#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(data.table))

script_argument <- commandArgs(FALSE)[grep("^--file=", commandArgs(FALSE))]
script_path <- sub("^--file=", "", script_argument[[1]])
root <- normalizePath(file.path(dirname(script_path), "..", ".."))
fixture <- file.path(root, "analysis", "tests", "fixtures")
test_root <- file.path(tempdir(), "lychee_primary_pathway_test")
dir.create(test_root, recursive = TRUE, showWarnings = FALSE)

counts <- fread(file.path(fixture, "counts.tsv"), check.names = FALSE)
setnames(counts, 1L, "gene_id")
counts_path <- file.path(test_root, "counts.tsv")
fwrite(counts, counts_path, sep = "\t")
metadata <- fread(file.path(fixture, "metadata.tsv"))
metadata_path <- file.path(test_root, "metadata.tsv")
fwrite(metadata, metadata_path, sep = "\t")
decisions_path <- file.path(test_root, "decisions.tsv")
fwrite(data.table(
  sample_id = metadata$sample_id,
  primary_status = "INCLUDE",
  reason = "none",
  all_sample_sensitivity = "retain"
), decisions_path, sep = "\t")
legacy_path <- file.path(test_root, "legacy.tsv")
fwrite(data.table(
  gene_id = sprintf("gene_%03d", 1:18),
  legacy_annotation = "synthetic_fixture"
), legacy_path, sep = "\t")
primary_out <- file.path(test_root, "primary")

status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "08_primary_discovery.R"),
  "--counts", counts_path, "--metadata", metadata_path,
  "--decisions", decisions_path,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--legacy", legacy_path, "--outdir", primary_out
))
if (status != 0L) stop("Primary discovery prerequisite failed")

gmt <- file.path(test_root, "synthetic.gmt")
writeLines(c(
  paste(c("positive_signal", "synthetic", sprintf("gene_%03d", c(1:8, 17:24))), collapse = "\t"),
  paste(c("negative_signal", "synthetic", sprintf("gene_%03d", c(9:16, 25:32))), collapse = "\t"),
  paste(c("null_set", "synthetic", sprintf("gene_%03d", 80:95)), collapse = "\t")
), gmt)
pathway_out <- file.path(test_root, "pathways")
status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "09_primary_pathways.R"),
  "--genes", file.path(primary_out, "all_genes_primary.tsv"),
  "--gmt", gmt,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--operational-config", file.path(root, "analysis", "config", "operational_qc.yaml"),
  "--outdir", pathway_out
))
if (status != 0L) stop("Primary pathway script failed")
observed <- fread(file.path(pathway_out, "all_pathways_primary.tsv"))
frozen_pathways <- fread(file.path(pathway_out, "frozen_pathways.tsv"))
stopifnot(
  nrow(observed) == 3L,
  observed[pathway == "positive_signal", NES] > 0,
  observed[pathway == "negative_signal", NES] < 0,
  nrow(frozen_pathways) >= 1L,
  file.exists(file.path(pathway_out, "frozen_pathways.tsv")),
  file.exists(file.path(pathway_out, "frozen_pathway_gene_statistics.tsv"))
)

primary_genes <- fread(file.path(primary_out, "all_genes_primary.tsv"))
gene_qc <- data.table(
  gene_id = primary_genes$gene_id,
  union_exon_bases = 400L + seq_len(nrow(primary_genes)),
  scored_exonic_bases = 400L + seq_len(nrow(primary_genes)),
  unique_exonic_bases = 400L + seq_len(nrow(primary_genes)),
  fraction_exonic_bases_scored = 1,
  fraction_unique_mappability = 1,
  mappability_status = "PASS",
  overlapping_gene_count = 0L,
  overlapping_genes = "",
  unique_gene_model_status = "PASS",
  uniform_gene_qc_status = "PASS"
)
gene_qc_path <- file.path(test_root, "gene_qc.tsv")
fwrite(gene_qc, gene_qc_path, sep = "\t")

robustness_out <- file.path(test_root, "pathway_robustness")
status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "13_internal_pathway_robustness.R"),
  "--counts", counts_path, "--metadata", metadata_path,
  "--decisions", decisions_path,
  "--primary-genes", file.path(primary_out, "all_genes_primary.tsv"),
  "--gene-qc", gene_qc_path,
  "--frozen-pathways", file.path(pathway_out, "frozen_pathways.tsv"),
  "--gmt", gmt,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--operational-config", file.path(root, "analysis", "config", "operational_qc.yaml"),
  "--outdir", robustness_out
))
if (status != 0L) stop("Internal pathway robustness script failed")
robustness <- fread(file.path(robustness_out, "frozen_pathway_robustness.tsv"))
stopifnot(
  nrow(robustness) == nrow(frozen_pathways),
  all(c("camera_pass", "roast_pass", "leading_edge_deletion_pass",
        "matched_random_pass", "internal_pathway_robustness_status") %in% names(robustness))
)

empty_dtu <- file.path(test_root, "empty_dtu.tsv")
fwrite(data.table(
  gene_id = character(), transcript_id = character(),
  dtu_status = character(), reason = character()
), empty_dtu, sep = "\t")
freeze_out <- file.path(test_root, "frozen_discovery")
status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "11_freeze_discovery.R"),
  "--genes", file.path(primary_out, "all_genes_primary.tsv"),
  "--gene-qc", gene_qc_path,
  "--pathways", file.path(pathway_out, "frozen_pathways.tsv"),
  "--pathway-genes", file.path(pathway_out, "frozen_pathway_gene_statistics.tsv"),
  "--dtu", empty_dtu,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--outdir", freeze_out
))
if (status != 0L) stop("Discovery freeze script failed")
stopifnot(
  nrow(fread(file.path(freeze_out, "frozen_genes.tsv"))) ==
    sum(primary_genes$statistical_discovery),
  file.exists(file.path(freeze_out, "frozen_results.sha256")),
  file.exists(file.path(freeze_out, "external_outcomes_unlock_timestamp.txt"))
)
cat("primary pathway, robustness, and discovery-freeze synthetic test PASS\n")
