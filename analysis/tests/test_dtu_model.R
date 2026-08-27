#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

script_argument <- commandArgs(FALSE)[grep("^--file=", commandArgs(FALSE))]
script_path <- sub("^--file=", "", script_argument[[1]])
root <- normalizePath(file.path(dirname(script_path), "..", ".."))
fixture <- file.path(root, "analysis", "tests", "fixtures")
test_root <- file.path(tempdir(), "lychee_dtu_model_test")
salmon_root <- file.path(test_root, "salmon")
dir.create(test_root, recursive = TRUE, showWarnings = FALSE)

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

set.seed(42017)
genes <- sprintf("gene%03d", 1:100)
transcripts <- as.vector(rbind(paste0(genes, "_a"), paste0(genes, "_b")))
for (sample_index in seq_len(nrow(metadata))) {
  sample <- metadata[sample_index]
  sample_root <- file.path(salmon_root, sample$sample_id)
  dir.create(file.path(sample_root, "aux_info"), recursive = TRUE, showWarnings = FALSE)
  counts <- numeric(length(transcripts))
  for (gene_index in seq_along(genes)) {
    signal <- gene_index <= 4L
    proportion <- if (
      signal && sample$cultivar == "Yurong1" && sample$treatment == "infected"
    ) 0.92 else 0.50
    concentration <- if (signal) 120 else 40
    observed_proportion <- rbeta(
      1L, proportion * concentration, (1 - proportion) * concentration
    )
    total <- sample(160:300, 1L)
    first <- round(total * max(0.05, min(0.95, observed_proportion)))
    counts[2L * gene_index - 1L] <- first
    counts[2L * gene_index] <- total - first
  }
  fwrite(data.table(
    Name = c(transcripts, "DECOY_CONTIG"),
    Length = c(rep(c(500L, 600L), length(genes)), 10000L),
    EffectiveLength = c(rep(c(400, 500), length(genes)), 9900),
    TPM = c(counts / sum(counts) * 1e6, 0),
    NumReads = c(counts, 0)
  ), file.path(sample_root, "quant.sf"), sep = "\t")
  write_json(list(
    percent_mapped = 90,
    num_bootstraps = 30
  ), file.path(sample_root, "aux_info", "meta_info.json"), auto_unbox = TRUE)
}

tx2gene_path <- file.path(test_root, "tx2gene.tsv")
fwrite(data.table(
  transcript_id = transcripts,
  gene_id = rep(genes, each = 2L)
), tx2gene_path, sep = "\t")
duplicates_path <- file.path(test_root, "duplicate_clusters.tsv")
fwrite(data.table(
  RetainedRef = character(), DuplicateRef = character()
), duplicates_path, sep = "\t")
config <- fromJSON(file.path(root, "analysis", "config", "discovery.yaml"), simplifyVector = FALSE)
config$dtu_gate$minimum_genes_with_multiple_isoforms <- 10L
config_path <- file.path(test_root, "discovery_test.json")
write_json(config, config_path, auto_unbox = TRUE, pretty = TRUE)
outdir <- file.path(test_root, "out")

status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "14_conditional_dtu.R"),
  "--metadata", metadata_path, "--decisions", decisions_path,
  "--salmon-root", salmon_root, "--tx2gene", tx2gene_path,
  "--duplicate-clusters", duplicates_path,
  "--config", config_path,
  "--operational-config", file.path(root, "analysis", "config", "operational_qc.yaml"),
  "--outdir", outdir
))
if (status != 0L) stop("Conditional DTU positive-control model failed")
gate <- fread(file.path(outdir, "dtu_gate.tsv"))
all_results <- fread(file.path(outdir, "all_dtu_results.tsv"))
nontranscript <- fread(file.path(outdir, "salmon_nontranscript_targets.tsv"))
stopifnot(
  all(gate$status == "PASS"),
  nrow(all_results) > 0L,
  any(all_results$dtu_status == "DISCOVERED"),
  nrow(nontranscript) == nrow(metadata),
  all(nontranscript$transcript_id == "DECOY_CONTIG"),
  all(all_results[dtu_status == "DISCOVERED"]$gene_id %in% genes[1:4]),
  file.exists(file.path(outdir, "drimseq_gene_results.tsv")),
  file.exists(file.path(outdir, "dexseq_sensitivity.tsv"))
)

# Reuse the planted Yurong1 treatment arm as a six-library Feizixiao-leaf
# cross-context fixture. Membership and expected direction come only from the
# already frozen discovery output.
external_metadata <- copy(metadata[cultivar == "Yurong1"])
external_metadata[, `:=`(cultivar = "Feizixiao", tissue = "leaf", time_h = "24")]
external_metadata_path <- file.path(test_root, "external_metadata.tsv")
external_decisions_path <- file.path(test_root, "external_decisions.tsv")
fwrite(external_metadata, external_metadata_path, sep = "\t")
fwrite(data.table(
  sample_id = external_metadata$sample_id,
  primary_status = "INCLUDE",
  reason = "none",
  all_sample_sensitivity = "retain"
), external_decisions_path, sep = "\t")
external_outdir <- file.path(test_root, "external_out")
external_status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "21_external_dtu.R"),
  "--frozen-dtu", file.path(outdir, "frozen_dtu_input.tsv"),
  "--metadata", external_metadata_path, "--decisions", external_decisions_path,
  "--salmon-root", salmon_root, "--tx2gene", tx2gene_path,
  "--discovery-config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--operational-config", file.path(root, "analysis", "config", "operational_qc.yaml"),
  "--external-config", file.path(root, "analysis", "config", "external_validation.yaml"),
  "--study", "PRJNA922966", "--outdir", external_outdir
))
if (external_status != 0L) stop("External DTU positive-control model failed")
external_results <- fread(file.path(external_outdir, "frozen_dtu_external_tests.tsv"))
external_nontranscript <- fread(file.path(external_outdir, "salmon_nontranscript_targets.tsv"))
stopifnot(
  nrow(external_results) == nrow(fread(file.path(outdir, "frozen_dtu_input.tsv"))),
  any(external_results$measurable),
  any(external_results$direction_agrees),
  nrow(external_nontranscript) == nrow(external_metadata),
  all(external_nontranscript$transcript_id == "DECOY_CONTIG")
)
cat("conditional DTU positive-control model test PASS\n")
