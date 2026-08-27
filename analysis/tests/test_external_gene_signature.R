#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(data.table))

set.seed(20260718)
root <- normalizePath(file.path(dirname(commandArgs(trailingOnly = FALSE)[grep("^--file=", commandArgs(trailingOnly = FALSE))]), "..", ".."), mustWork = FALSE)
root <- normalizePath(".")
script <- file.path(root, "analysis/scripts/18_external_gene_signature.R")
pathway_script <- file.path(root, "analysis/scripts/19_external_pathways.R")
config <- file.path(root, "analysis/config/external_validation.yaml")
discovery_config <- file.path(root, "analysis/config/discovery.yaml")

make_metadata <- function(study) {
  if (study == "PRJNA450886") {
    value <- CJ(cultivar = c("Guiwei", "Heiye"), treatment = c("mock", "infected"),
                time_h = c("6", "24", "48"), replicate = 1:3)
    value[, tissue := "pericarp"]
  } else if (study == "PRJNA922966") {
    value <- CJ(tissue = c("fruit", "leaf"), treatment = c("mock", "infected"), replicate = 1:3)
    value[, `:=`(cultivar = "Feizixiao", time_h = "24")]
  } else {
    value <- CJ(cultivar = c("Guiwei", "SFZ_unresolved"), treatment = c("mock", "infected"), replicate = 1:3)
    value[, `:=`(tissue = "leaf", time_h = "unreported")]
  }
  value[, sample_id := sprintf("%s_%02d", study, .I)]
  value
}

run_study <- function(study) {
  directory <- file.path(tempdir(), paste0("external-test-", study))
  unlink(directory, recursive = TRUE)
  dir.create(directory, recursive = TRUE)
  metadata <- make_metadata(study)
  genes <- sprintf("gene_%03d", 1:250)
  mean_matrix <- matrix(
    rep(exp(runif(length(genes), log(50), log(500))), nrow(metadata)),
    nrow = length(genes)
  )
  if (study == "PRJNA450886") {
    primary <- metadata$cultivar == "Heiye" & metadata$treatment == "infected" & metadata$time_h == "24"
    mean_matrix[1:4, primary] <- mean_matrix[1:4, primary] * 8
  } else if (study == "PRJNA922966") {
    primary <- metadata$tissue == "leaf" & metadata$treatment == "infected"
    mean_matrix[1:4, primary] <- mean_matrix[1:4, primary] * 6
  } else {
    primary <- metadata$cultivar == "SFZ_unresolved" & metadata$treatment == "infected"
    mean_matrix[1:4, primary] <- mean_matrix[1:4, primary] * 6
  }
  count_matrix <- matrix(
    rnbinom(length(mean_matrix), mu = as.vector(mean_matrix), size = 20),
    nrow = nrow(mean_matrix), dimnames = list(genes, metadata$sample_id)
  )
  counts <- as.data.table(count_matrix, keep.rownames = "gene_id")
  decisions <- metadata[, .(
    sample_id, primary_status = "INCLUDE", reason = "none", all_sample_sensitivity = "retain"
  )]
  frozen <- data.table(
    gene_id = genes[1:4], interaction_log2fc = rep(2, 4), interaction_q = rep(0.001, 4),
    uniform_gene_qc_status = "PASS"
  )
  signature <- data.table(
    gene_id = genes[1:4], weight = rep(2, 4),
    expected_direction = "stronger_in_resistant", primary_interaction_log2fc = 2,
    primary_q = 0.001
  )
  paths <- list(
    counts = file.path(directory, "counts.tsv"),
    metadata = file.path(directory, "metadata.tsv"),
    decisions = file.path(directory, "decisions.tsv"),
    frozen = file.path(directory, "frozen.tsv"),
    signature = file.path(directory, "signature.tsv"),
    output = file.path(directory, "output"),
    pathway_output = file.path(directory, "pathways"),
    frozen_pathways = file.path(directory, "frozen_pathways.tsv"),
    frozen_pathway_genes = file.path(directory, "frozen_pathway_genes.tsv"),
    gmt = file.path(directory, "pathways.gmt"),
    gene_qc = file.path(directory, "gene_qc.tsv")
  )
  fwrite(counts, paths$counts, sep = "\t")
  fwrite(metadata, paths$metadata, sep = "\t")
  fwrite(decisions, paths$decisions, sep = "\t")
  fwrite(frozen, paths$frozen, sep = "\t")
  fwrite(signature, paths$signature, sep = "\t")
  frozen_pathways <- data.table(
    pathway = c("planted_pathway", "null_pathway"),
    NES = c(2, -1), padj = c(0.001, 0.02)
  )
  frozen_pathway_genes <- rbindlist(list(
    data.table(
      pathway = "planted_pathway", gene_id = genes[1:20],
      signed_wald_stat = c(rep(4, 4), rep(1, 16)), leading_edge = genes[1:20] %in% genes[1:10]
    ),
    data.table(
      pathway = "null_pathway", gene_id = genes[31:50],
      signed_wald_stat = rep(-1, 20), leading_edge = genes[31:50] %in% genes[31:40]
    )
  ))
  fwrite(frozen_pathways, paths$frozen_pathways, sep = "\t")
  fwrite(frozen_pathway_genes, paths$frozen_pathway_genes, sep = "\t")
  writeLines(c(
    paste(c("planted_pathway", "synthetic", genes[1:20]), collapse = "\t"),
    paste(c("null_pathway", "synthetic", genes[31:50]), collapse = "\t")
  ), paths$gmt)
  fwrite(data.table(gene_id = genes, union_exon_bases = seq(500, 1745, by = 5)),
         paths$gene_qc, sep = "\t")
  status <- system2(
    file.path(R.home("bin"), "Rscript"),
    c(
      script,
      "--counts", paths$counts, "--metadata", paths$metadata,
      "--decisions", paths$decisions, "--frozen-genes", paths$frozen,
      "--frozen-signature", paths$signature, "--config", config,
      "--study", study, "--outdir", paths$output
    )
  )
  stopifnot(status == 0L)
  gene_tests <- fread(file.path(paths$output, "frozen_gene_tests.tsv"))
  signature_tests <- fread(file.path(paths$output, "signature_contrasts.tsv"))
  stopifnot(nrow(gene_tests) == 4L * ifelse(study == "PRJNA1090613", 1L, 3L))
  stopifnot(nrow(signature_tests) == ifelse(study == "PRJNA1090613", 1L, 3L))
  stopifnot(all(is.finite(signature_tests$estimate)))
  if (study == "PRJNA450886") {
    stopifnot(all(gene_tests[contrast == "primary_24h", direction_agrees]))
    stopifnot(signature_tests[contrast == "primary_24h", estimate] > 0)
  }
  pathway_status <- system2(
    file.path(R.home("bin"), "Rscript"),
    c(
      pathway_script,
      "--counts", paths$counts, "--metadata", paths$metadata,
      "--decisions", paths$decisions,
      "--external-genes", file.path(paths$output, "all_gene_contrasts.tsv"),
      "--frozen-pathways", paths$frozen_pathways,
      "--frozen-pathway-genes", paths$frozen_pathway_genes,
      "--gmt", paths$gmt, "--gene-qc", paths$gene_qc,
      "--discovery-config", discovery_config, "--external-config", config,
      "--study", study, "--outdir", paths$pathway_output
    )
  )
  stopifnot(pathway_status == 0L)
  pathway_tests <- fread(file.path(paths$pathway_output, "frozen_pathway_tests.tsv"))
  stopifnot(nrow(pathway_tests) == 2L)
  stopifnot(all(pathway_tests$study == study))
}

for (study in c("PRJNA450886", "PRJNA922966", "PRJNA1090613")) run_study(study)
cat("external gene/signature synthetic tests PASS\n")
