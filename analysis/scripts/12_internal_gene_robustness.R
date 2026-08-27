#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DESeq2)
  library(edgeR)
  library(tximport)
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

prepare_metadata <- function(metadata) {
  metadata <- copy(metadata)
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Yurong1"))]
  metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
  if (anyNA(metadata$cultivar) || anyNA(metadata$treatment)) stop("Unexpected factor level")
  matrix <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
  if (qr(matrix)$rank != ncol(matrix)) stop("Design is not full rank")
  metadata
}

coldata <- function(metadata) {
  value <- as.data.frame(metadata)
  rownames(value) <- value$sample_id
  value
}

fit_deseq_matrix <- function(counts, metadata, keep) {
  dds <- DESeqDataSetFromMatrix(
    countData = round(counts[keep, , drop = FALSE]),
    colData = coldata(metadata),
    design = ~ cultivar + treatment + cultivar:treatment
  )
  dds <- DESeq(
    dds, test = "Wald", quiet = TRUE, parallel = FALSE,
    minReplicatesForReplace = Inf
  )
  coefficient <- "cultivarYurong1.treatmentinfected"
  if (!coefficient %in% resultsNames(dds)) stop("Locked coefficient not available")
  result <- as.data.table(results(
    dds, name = coefficient, independentFiltering = FALSE, cooksCutoff = FALSE
  ), keep.rownames = "gene_id")
  setnames(
    result,
    c("log2FoldChange", "lfcSE", "stat", "pvalue", "padj"),
    c("interaction_log2fc", "interaction_lfc_se", "signed_stat", "p", "q")
  )
  result
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "counts", "primary-genes", "frozen-genes", "metadata", "decisions",
  "salmon-root", "tx2gene", "mapping-sensitivity", "config", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))
config <- fromJSON(args$config, simplifyVector = TRUE)
set.seed(as.integer(config$random_seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

count_table <- fread(args$counts, check.names = FALSE)
if (names(count_table)[1L] != "gene_id") stop("Count table must begin with gene_id")
counts <- as.matrix(count_table[, -1L])
rownames(counts) <- count_table$gene_id
storage.mode(counts) <- "numeric"
metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)[primary_status == "INCLUDE"]
if (!setequal(metadata$sample_id, colnames(counts))) {
  stop("Robustness count matrix and included metadata differ")
}
metadata <- metadata[match(colnames(counts), sample_id)]
metadata <- prepare_metadata(metadata)
primary <- fread(args[["primary-genes"]])
frozen <- fread(args[["frozen-genes"]])
mapping_sensitivity <- fread(args[["mapping-sensitivity"]])
if (nrow(frozen) && !all(frozen$gene_id %in% mapping_sensitivity$gene_id)) {
  stop("Observed mapping sensitivity is missing a frozen gene")
}

minimum_count <- as.integer(config$primary_filter$minimum_count)
minimum_libraries <- as.integer(config$primary_filter$minimum_libraries)
primary_keep <- rowSums(counts >= minimum_count) >= minimum_libraries

# Salmon/tximport sensitivity.
salmon_files <- file.path(args[["salmon-root"]], metadata$sample_id, "quant.sf")
names(salmon_files) <- metadata$sample_id
if (any(!file.exists(salmon_files))) stop("Missing Salmon quantification files")
tx2gene <- fread(args$tx2gene)[, 1:2]
txi <- tximport(
  salmon_files, type = "salmon", tx2gene = tx2gene,
  countsFromAbundance = "no", ignoreTxVersion = FALSE
)
salmon_metadata <- metadata[match(colnames(txi$counts), sample_id)]
salmon_keep <- rowSums(txi$counts >= minimum_count) >= minimum_libraries
salmon_dds <- DESeqDataSetFromTximport(
  txi,
  colData = coldata(salmon_metadata),
  design = ~ cultivar + treatment + cultivar:treatment
)
salmon_dds <- salmon_dds[salmon_keep, ]
salmon_dds <- DESeq(
  salmon_dds, test = "Wald", quiet = TRUE, parallel = FALSE,
  minReplicatesForReplace = Inf
)
salmon_coefficient <- "cultivarYurong1.treatmentinfected"
salmon_result <- as.data.table(results(
  salmon_dds, name = salmon_coefficient,
  independentFiltering = FALSE, cooksCutoff = FALSE
), keep.rownames = "gene_id")
setnames(
  salmon_result,
  c("log2FoldChange", "lfcSE", "stat", "pvalue", "padj"),
  c("salmon_interaction_log2fc", "salmon_lfc_se", "salmon_signed_stat", "salmon_p", "salmon_q")
)

# edgeR quasi-likelihood sensitivity on primary featureCounts.
design <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
interaction_column <- grep("cultivarYurong1:treatmentinfected", colnames(design), fixed = TRUE)
if (length(interaction_column) != 1L) stop("edgeR interaction column was not unique")
dge <- DGEList(counts = counts[primary_keep, , drop = FALSE])
dge <- calcNormFactors(dge)
dge <- estimateDisp(dge, design, robust = TRUE)
edge_fit <- glmQLFit(dge, design, robust = TRUE)
edge_test <- glmQLFTest(edge_fit, coef = interaction_column)
edge_result <- as.data.table(topTags(edge_test, n = Inf, sort.by = "none")$table,
                             keep.rownames = "gene_id")
setnames(
  edge_result,
  c("logFC", "F", "PValue", "FDR"),
  c("edgeR_interaction_log2fc", "edgeR_F", "edgeR_p", "edgeR_q")
)
edge_result[, edgeR_signed_stat := sign(edgeR_interaction_log2fc) * sqrt(edgeR_F)]
write_tsv(edge_result, file.path(args$outdir, "edgeR_all_genes.tsv"))

# CPM-filter sensitivity with the same DESeq2 coefficient.
cpm_keep <- rowSums(cpm(DGEList(counts = counts)) >
                      as.numeric(config$sensitivity_filter$minimum_cpm)) >=
  as.integer(config$sensitivity_filter$minimum_libraries)
cpm_result <- fit_deseq_matrix(counts, metadata, cpm_keep)
setnames(
  cpm_result,
  c("interaction_log2fc", "interaction_lfc_se", "signed_stat", "p", "q"),
  c("cpm_filter_log2fc", "cpm_filter_lfc_se", "cpm_filter_stat", "cpm_filter_p", "cpm_filter_q")
)
write_tsv(cpm_result, file.path(args$outdir, "cpm_filter_all_genes.tsv"))

# FeatureCounts versus Salmon genome-wide concordance.
comparison <- merge(
  primary[, .(
    gene_id,
    featurecounts_log2fc = interaction_log2fc,
    featurecounts_signed_stat = signed_wald_stat,
    featurecounts_q = interaction_q
  )],
  salmon_result,
  by = "gene_id", all = TRUE, sort = FALSE
)
finite <- comparison[
  is.finite(featurecounts_signed_stat) & is.finite(salmon_signed_stat)
]
signed_rho <- if (nrow(finite) >= 3L) {
  cor(finite$featurecounts_signed_stat, finite$salmon_signed_stat, method = "spearman")
} else {
  NA_real_
}
write_tsv(comparison, file.path(args$outdir, "quantification_method_comparison.tsv"))

# All twelve leave-one-library-out fits, evaluated only for frozen genes.
if (nrow(frozen)) {
  leave_one_out <- rbindlist(lapply(metadata$sample_id, function(omitted) {
    kept_samples <- setdiff(metadata$sample_id, omitted)
    subset_metadata <- prepare_metadata(metadata[sample_id %in% kept_samples])
    subset_metadata <- subset_metadata[match(kept_samples, sample_id)]
    subset_counts <- counts[, kept_samples, drop = FALSE]
    keep <- rowSums(subset_counts >= minimum_count) >= minimum_libraries
    result <- fit_deseq_matrix(subset_counts, subset_metadata, keep)
    merged <- merge(
      frozen[, .(gene_id, primary_interaction_log2fc = interaction_log2fc)],
      result[, .(gene_id, loo_log2fc = interaction_log2fc, loo_p = p, loo_q = q)],
      by = "gene_id", all.x = TRUE, sort = FALSE
    )
    merged[, omitted_sample := omitted]
    merged[, sign_agrees := !is.na(loo_log2fc) &
             sign(loo_log2fc) == sign(primary_interaction_log2fc)]
    merged[, .(
      gene_id, omitted_sample, primary_interaction_log2fc,
      loo_log2fc, loo_p, loo_q, sign_agrees
    )]
  }))
} else {
  leave_one_out <- data.table(
    gene_id = character(), omitted_sample = character(),
    primary_interaction_log2fc = numeric(), loo_log2fc = numeric(),
    loo_p = numeric(), loo_q = numeric(), sign_agrees = logical()
  )
}
write_tsv(leave_one_out, file.path(args$outdir, "leave_one_library_out.tsv"))

# Deterministic frozen-gene pass/fail matrix.
if (nrow(frozen)) {
  candidate <- frozen[, .(
    gene_id,
    primary_interaction_log2fc = interaction_log2fc,
    primary_q = interaction_q,
    mapping_qc = uniform_gene_qc_status
  )]
  candidate <- merge(candidate, salmon_result[, .(
    gene_id, salmon_interaction_log2fc, salmon_q
  )], by = "gene_id", all.x = TRUE, sort = FALSE)
  candidate <- merge(candidate, edge_result[, .(
    gene_id, edgeR_interaction_log2fc, edgeR_q
  )], by = "gene_id", all.x = TRUE, sort = FALSE)
  candidate <- merge(candidate, cpm_result[, .(
    gene_id, cpm_filter_log2fc, cpm_filter_q
  )], by = "gene_id", all.x = TRUE, sort = FALSE)
  candidate <- merge(candidate, mapping_sensitivity[, .(
    gene_id, observed_mapping_sensitivity_status
  )], by = "gene_id", all.x = TRUE, sort = FALSE)
  loo_summary <- leave_one_out[, .(
    loo_sign_agreement_count = sum(sign_agrees, na.rm = TRUE),
    loo_q_below_threshold_count = sum(
      !is.na(loo_q) & loo_q < as.numeric(config$internal_robustness$leave_one_out_q_max)
    )
  ), by = gene_id]
  candidate <- merge(candidate, loo_summary, by = "gene_id", all.x = TRUE, sort = FALSE)
  candidate[, salmon_sign_agreement := !is.na(salmon_interaction_log2fc) &
              sign(salmon_interaction_log2fc) == sign(primary_interaction_log2fc)]
  candidate[, salmon_absolute_lfc_difference :=
              abs(salmon_interaction_log2fc - primary_interaction_log2fc)]
  candidate[, edgeR_sign_agreement := !is.na(edgeR_interaction_log2fc) &
              sign(edgeR_interaction_log2fc) == sign(primary_interaction_log2fc)]
  candidate[, cpm_filter_sign_agreement := !is.na(cpm_filter_log2fc) &
              sign(cpm_filter_log2fc) == sign(primary_interaction_log2fc)]
  candidate[, quantification_pass :=
              !is.na(signed_rho) &
              signed_rho >= as.numeric(config$internal_robustness$signed_statistic_spearman_min) &
              salmon_sign_agreement &
              salmon_absolute_lfc_difference <=
                as.numeric(config$internal_robustness$maximum_absolute_lfc_difference)]
  candidate[, statistical_method_pass :=
              edgeR_sign_agreement &
              primary_q < as.numeric(config$internal_robustness$method_q_max) &
              !is.na(edgeR_q) & edgeR_q < as.numeric(config$internal_robustness$method_q_max)]
  candidate[, filter_pass := cpm_filter_sign_agreement]
  candidate[, leave_one_out_pass :=
              loo_sign_agreement_count >=
                as.integer(config$internal_robustness$leave_one_out_sign_required) &
              loo_q_below_threshold_count >=
                as.integer(config$internal_robustness$leave_one_out_q_required)]
  candidate[, internal_robustness_status := fifelse(
    quantification_pass & statistical_method_pass & filter_pass &
      leave_one_out_pass & mapping_qc == "PASS" &
      !grepl("^FAIL", observed_mapping_sensitivity_status),
    "PASS", "FAIL"
  )]
} else {
  candidate <- data.table(
    gene_id = character(), primary_interaction_log2fc = numeric(), primary_q = numeric(),
    mapping_qc = character(), salmon_interaction_log2fc = numeric(), salmon_q = numeric(),
    edgeR_interaction_log2fc = numeric(), edgeR_q = numeric(),
    cpm_filter_log2fc = numeric(), cpm_filter_q = numeric(),
    observed_mapping_sensitivity_status = character(),
    loo_sign_agreement_count = integer(), loo_q_below_threshold_count = integer(),
    salmon_sign_agreement = logical(), salmon_absolute_lfc_difference = numeric(),
    edgeR_sign_agreement = logical(), cpm_filter_sign_agreement = logical(),
    quantification_pass = logical(), statistical_method_pass = logical(),
    filter_pass = logical(), leave_one_out_pass = logical(),
    internal_robustness_status = character()
  )
}
write_tsv(candidate, file.path(args$outdir, "frozen_gene_robustness.tsv"))

summary <- data.table(
  metric = c(
    "featurecounts_filtered_genes", "salmon_filtered_genes",
    "common_finite_signed_statistics", "signed_statistic_spearman",
    "signed_statistic_spearman_threshold", "frozen_genes",
    "robust_frozen_genes"
  ),
  value = c(
    sum(primary_keep), sum(salmon_keep), nrow(finite), signed_rho,
    as.numeric(config$internal_robustness$signed_statistic_spearman_min),
    nrow(frozen), sum(candidate$internal_robustness_status == "PASS")
  ),
  status = c(
    "INFO", "INFO", "INFO",
    ifelse(!is.na(signed_rho) && signed_rho >=
             as.numeric(config$internal_robustness$signed_statistic_spearman_min),
           "PASS", "FAIL"),
    "LOCKED", "INFO", "INFO"
  )
)
write_tsv(summary, file.path(args$outdir, "robustness_summary.tsv"))
writeLines(c(
  "# Internal gene robustness",
  "",
  sprintf("- FeatureCounts/Salmon signed-statistic Spearman rho: %.4f (pass >= %.2f)",
          signed_rho, as.numeric(config$internal_robustness$signed_statistic_spearman_min)),
  sprintf("- Frozen genes: %d", nrow(frozen)),
  sprintf("- Genes passing every internal robustness gate: %d",
          sum(candidate$internal_robustness_status == "PASS")),
  "- These results do not use any external dataset."
), file.path(args$outdir, "robustness_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "robustness_sessionInfo.txt"))
