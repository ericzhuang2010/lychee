#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

parse_args <- function(args) {
  if (length(args) %% 2L != 0L) stop("Arguments must be --key value pairs")
  keys <- sub("^--", "", args[seq(1L, length(args), by = 2L)])
  values <- args[seq(2L, length(args), by = 2L)]
  setNames(as.list(values), keys)
}

write_tsv <- function(x, path) {
  fwrite(as.data.table(x), path, sep = "\t", quote = FALSE, na = "NA")
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "genes", "gene-qc", "pathways", "pathway-genes", "dtu",
  "config", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))
config <- fromJSON(args$config, simplifyVector = TRUE)
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

genes <- fread(args$genes)
gene_qc <- fread(args[["gene-qc"]])
if (anyDuplicated(gene_qc$gene_id)) stop("Duplicate genes in uniform gene QC")
placeholder_columns <- intersect(
  c("mappability_status", "unique_gene_model_status", "primary_gene_status"),
  names(genes)
)
if (length(placeholder_columns)) genes[, (placeholder_columns) := NULL]
status <- merge(genes, gene_qc, by = "gene_id", all.x = TRUE, sort = FALSE)
if (anyNA(status$uniform_gene_qc_status)) {
  missing_ids <- status[is.na(uniform_gene_qc_status), head(gene_id, 10L)]
  stop("Uniform gene QC missing for filtered genes: ", paste(missing_ids, collapse = ","))
}
status[, primary_gene_status := fcase(
  statistical_discovery == TRUE & mappability_status != "PASS",
    "RETIRED_MAPPING_FAILURE",
  statistical_discovery == TRUE & unique_gene_model_status != "PASS",
    "RETIRED_GENE_MODEL_AMBIGUITY",
  statistical_discovery == TRUE & uniform_gene_qc_status == "PASS",
    "DISCOVERED",
  default = "NOT_STATISTICAL_DISCOVERY"
)]
setorder(status, interaction_p, gene_id, na.last = TRUE)
write_tsv(status, file.path(args$outdir, "all_gene_discovery_status.tsv"))

frozen_genes <- status[primary_gene_status == "DISCOVERED"]
write_tsv(frozen_genes, file.path(args$outdir, "frozen_genes.tsv"))
if (nrow(frozen_genes)) {
  signature <- frozen_genes[, .(
    gene_id,
    weight = shrunken_interaction_log2fc,
    expected_direction = fifelse(
      shrunken_interaction_log2fc > 0,
      "stronger_infection_response_in_Yurong1",
      "stronger_infection_response_in_Guiwei"
    ),
    primary_interaction_log2fc = interaction_log2fc,
    primary_q = interaction_q
  )]
} else {
  signature <- data.table(
    gene_id = character(), weight = numeric(), expected_direction = character(),
    primary_interaction_log2fc = numeric(), primary_q = numeric()
  )
}
write_tsv(signature, file.path(args$outdir, "frozen_signature.tsv"))

pathways <- fread(args$pathways)
pathway_genes <- fread(args[["pathway-genes"]])
dtu <- fread(args$dtu)
write_tsv(pathways, file.path(args$outdir, "frozen_pathways.tsv"))
write_tsv(pathway_genes, file.path(args$outdir, "frozen_pathway_gene_statistics.tsv"))
write_tsv(dtu, file.path(args$outdir, "frozen_dtu.tsv"))

summary_lines <- c(
  "# Frozen discovery summary",
  "",
  sprintf("- Statistical gene candidates before uniform gene QC: %d",
          sum(status$statistical_discovery == TRUE, na.rm = TRUE)),
  sprintf("- Frozen genes after mappability and unique-model QC: %d", nrow(frozen_genes)),
  sprintf("- Frozen pathways at the primary pathway threshold: %d", nrow(pathways)),
  sprintf("- Frozen DTU rows after the conditional gate: %d", nrow(dtu)),
  if (nrow(frozen_genes)) {
    "- The signed gene signature uses apeglm-shrunken interaction effects as weights."
  } else {
    "- The frozen gene signature is empty; only the preregistered pathway fallback may advance."
  },
  "- Positive effects mean a stronger infection response in Yurong1 than Guiwei.",
  "- External outcomes were closed until the checksum bundle below was written."
)
writeLines(summary_lines, file.path(args$outdir, "discovery_summary.md"))

frozen_paths <- sort(list.files(args$outdir, pattern = "^frozen_.*\\.tsv$", full.names = TRUE))
if (length(frozen_paths) != 5L) {
  stop("Expected exactly five frozen TSV artifacts, observed ", length(frozen_paths))
}
checksums <- system2("sha256sum", frozen_paths, stdout = TRUE, stderr = TRUE)
status_code <- attr(checksums, "status")
if (!is.null(status_code) && status_code != 0L) stop("sha256sum failed")
writeLines(checksums, file.path(args$outdir, "frozen_results.sha256"))
verify <- system2(
  "sha256sum", c("-c", file.path(args$outdir, "frozen_results.sha256")),
  stdout = TRUE, stderr = TRUE
)
verify_status <- attr(verify, "status")
if (!is.null(verify_status) && verify_status != 0L) {
  stop("Frozen discovery checksum verification failed: ", paste(verify, collapse = "; "))
}
writeLines(
  c(
    format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    "Frozen result checksum verification PASS.",
    "External outcomes may now be opened by the prespecified scripts."
  ),
  file.path(args$outdir, "external_outcomes_unlock_timestamp.txt")
)
