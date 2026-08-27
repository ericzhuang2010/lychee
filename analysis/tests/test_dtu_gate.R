#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

script_argument <- commandArgs(FALSE)[grep("^--file=", commandArgs(FALSE))]
script_path <- sub("^--file=", "", script_argument[[1]])
root <- normalizePath(file.path(dirname(script_path), "..", ".."))
fixture <- file.path(root, "analysis", "tests", "fixtures")
test_root <- file.path(tempdir(), "lychee_dtu_gate_test")
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

for (sample_id in metadata$sample_id) {
  sample_root <- file.path(salmon_root, sample_id)
  dir.create(file.path(sample_root, "aux_info"), recursive = TRUE, showWarnings = FALSE)
  fwrite(data.table(
    Name = c("tx1", "tx2", "DECOY_CONTIG"), Length = c(500L, 600L, 10000L),
    EffectiveLength = c(400, 500, 9900), TPM = c(60, 40, 0), NumReads = c(60, 40, 0)
  ), file.path(sample_root, "quant.sf"), sep = "\t")
  write_json(list(
    percent_mapped = 90,
    num_bootstraps = 30
  ), file.path(sample_root, "aux_info", "meta_info.json"), auto_unbox = TRUE)
}
tx2gene_path <- file.path(test_root, "tx2gene.tsv")
fwrite(data.table(
  transcript_id = c("tx1", "tx2"), gene_id = c("gene1", "gene1")
), tx2gene_path, sep = "\t")
duplicates_path <- file.path(test_root, "duplicate_clusters.tsv")
fwrite(data.table(
  RetainedRef = character(), DuplicateRef = character()
), duplicates_path, sep = "\t")
outdir <- file.path(test_root, "out")

status <- system2(file.path(R.home("bin"), "Rscript"), c(
  file.path(root, "analysis", "scripts", "14_conditional_dtu.R"),
  "--metadata", metadata_path, "--decisions", decisions_path,
  "--salmon-root", salmon_root, "--tx2gene", tx2gene_path,
  "--duplicate-clusters", duplicates_path,
  "--config", file.path(root, "analysis", "config", "discovery.yaml"),
  "--operational-config", file.path(root, "analysis", "config", "operational_qc.yaml"),
  "--outdir", outdir
))
if (status != 0L) stop("Conditional DTU gate script failed")
gate <- fread(file.path(outdir, "dtu_gate.tsv"))
frozen <- fread(file.path(outdir, "frozen_dtu_input.tsv"))
nontranscript <- fread(file.path(outdir, "salmon_nontranscript_targets.tsv"))
stopifnot(
  gate[gate == "genes_with_at_least_two_retained_isoforms", status] == "FAIL",
  nrow(frozen) == 0L,
  nrow(nontranscript) == nrow(metadata),
  all(nontranscript$transcript_id == "DECOY_CONTIG"),
  all(nontranscript$count == 0),
  file.exists(file.path(outdir, "dtu_summary.md")),
  !file.exists(file.path(outdir, "drimseq_gene_results.tsv"))
)
cat("conditional DTU fail-closed gate test PASS\n")
