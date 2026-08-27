#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(data.table))

directory <- file.path(tempdir(), "external-dtu-empty")
unlink(directory, recursive = TRUE)
dir.create(directory, recursive = TRUE)
frozen <- file.path(directory, "frozen.tsv")
fwrite(data.table(
  gene_id = character(), transcript_id = character(), stage_gene_q = numeric(),
  stage_transcript_q = numeric(), usage_interaction_difference = numeric(),
  expected_direction = character(), exact_sequence_duplicate_status = character(),
  transcript_mappability_status = character(), dtu_status = character(), reason = character()
), frozen, sep = "\t")
output <- file.path(directory, "output")
status <- system2(
  file.path(R.home("bin"), "Rscript"),
  c(
    "analysis/scripts/21_external_dtu.R",
    "--frozen-dtu", frozen, "--metadata", "unused_metadata.tsv",
    "--decisions", "unused_decisions.tsv", "--salmon-root", "unused_salmon",
    "--tx2gene", "unused_tx2gene.tsv",
    "--discovery-config", "analysis/config/discovery.yaml",
    "--operational-config", "analysis/config/operational_qc.yaml",
    "--external-config", "analysis/config/external_validation.yaml",
    "--study", "PRJNA450886", "--outdir", output
  )
)
stopifnot(status == 0L)
result <- fread(file.path(output, "frozen_dtu_external_tests.tsv"))
gate <- fread(file.path(output, "external_dtu_gate.tsv"))
nontranscript <- fread(file.path(output, "salmon_nontranscript_targets.tsv"))
stopifnot(
  nrow(result) == 0L,
  gate$status == "NOT_APPLICABLE",
  nrow(nontranscript) == 0L,
  identical(names(nontranscript), c(
    "transcript_id", "sample_id", "count", "exclusion_reason"
  ))
)
cat("external DTU empty-gate test PASS\n")
