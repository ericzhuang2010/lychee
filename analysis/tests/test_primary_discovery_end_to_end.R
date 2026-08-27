#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(data.table))

script_argument <- commandArgs(FALSE)[grep("^--file=", commandArgs(FALSE))]
script_path <- sub("^--file=", "", script_argument[[1]])
root <- normalizePath(file.path(dirname(script_path), "..", ".."))
fixture <- file.path(root, "analysis", "tests", "fixtures")
test_root <- file.path(tempdir(), "lychee_primary_discovery_test")
dir.create(test_root, recursive = TRUE, showWarnings = FALSE)

counts <- fread(file.path(fixture, "counts.tsv"), check.names = FALSE)
setnames(counts, 1L, "gene_id")
counts_path <- file.path(test_root, "counts.tsv")
fwrite(counts, counts_path, sep = "\t")

metadata <- fread(file.path(fixture, "metadata.tsv"))
metadata_path <- file.path(test_root, "metadata.tsv")
fwrite(metadata, metadata_path, sep = "\t")

decisions <- data.table(
  sample_id = metadata$sample_id,
  primary_status = "INCLUDE",
  reason = "none",
  all_sample_sensitivity = "retain"
)
decisions_path <- file.path(test_root, "decisions.tsv")
fwrite(decisions, decisions_path, sep = "\t")

legacy <- data.table(
  gene_id = sprintf("gene_%03d", 1:18),
  legacy_annotation = "synthetic_fixture"
)
legacy_path <- file.path(test_root, "legacy.tsv")
fwrite(legacy, legacy_path, sep = "\t")
outdir <- file.path(test_root, "results")

command <- c(
  file.path(root, "analysis", "scripts", "08_primary_discovery.R"),
  "--counts", counts_path,
  "--metadata", metadata_path,
  "--decisions", decisions_path,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--legacy", legacy_path,
  "--outdir", outdir
)
status <- system2(file.path(R.home("bin"), "Rscript"), command)
if (status != 0L) stop("Primary discovery script failed on synthetic fixture")

observed <- fread(file.path(outdir, "all_genes_primary.tsv"))
expected <- fread(file.path(fixture, "expected_results.tsv"))
signals <- merge(
  expected[expected_class == "interaction"],
  observed,
  by = "gene_id",
  all.x = TRUE
)
stopifnot(
  nrow(signals) == 16L,
  all(signals$statistical_discovery),
  all(signals[expected_sign == "positive"]$interaction_log2fc > 0),
  all(signals[expected_sign == "negative"]$interaction_log2fc < 0),
  file.exists(file.path(outdir, "interaction_lrt.tsv")),
  file.exists(file.path(outdir, "legacy_18_audit.tsv")),
  file.exists(file.path(outdir, "pca_samples.pdf"))
)
cat("primary discovery end-to-end synthetic test PASS\n")
