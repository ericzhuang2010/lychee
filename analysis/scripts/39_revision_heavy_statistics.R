#!/usr/bin/env Rscript

# Heavy-machine reviewer-response analyses H1 and H2.
# H1 refits genome-wide infected-versus-mock models within each cultivar.
# H2 applies a post hoc composite-null interaction test and apeglm s-values.

suppressPackageStartupMessages({
  library(data.table)
  library(DESeq2)
  library(apeglm)
  library(jsonlite)
})

parse_args <- function(args) {
  if (length(args) %% 2L != 0L) stop("Arguments must be --key value pairs")
  keys <- sub("^--", "", args[seq(1L, length(args), by = 2L)])
  values <- args[seq(2L, length(args), by = 2L)]
  setNames(as.list(values), keys)
}

write_tsv <- function(x, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  fwrite(as.data.table(x), path, sep = "\t", quote = FALSE, na = "NA")
}

as_flag <- function(x) {
  !is.na(x) & x
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "counts", "metadata", "decisions", "config", "legacy", "s3", "robustness",
  "supplement_out", "sensitivity_out", "summary_out", "workdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

config <- fromJSON(args$config, simplifyVector = TRUE)
lfc_min <- as.numeric(config$gene_discovery$absolute_log2fc_min)
q_max <- as.numeric(config$gene_discovery$bh_q_max)
set.seed(as.integer(config$random_seed))
dir.create(args$workdir, recursive = TRUE, showWarnings = FALSE)

count_table <- fread(args$counts, check.names = FALSE)
if (names(count_table)[1] != "gene_id") stop("Count matrix must start with gene_id")
if (anyDuplicated(count_table$gene_id)) stop("Count matrix has duplicated genes")
counts_all <- as.matrix(count_table[, -1])
rownames(counts_all) <- count_table$gene_id
storage.mode(counts_all) <- "integer"
if (any(counts_all < 0L)) stop("Counts must be nonnegative")

metadata <- fread(args$metadata)
decisions <- fread(args$decisions)
metadata <- merge(metadata, decisions, by = "sample_id", all.x = TRUE, sort = FALSE)
metadata <- metadata[primary_status == "INCLUDE"]
if (!setequal(colnames(counts_all), metadata$sample_id)) {
  stop("Included metadata and count-matrix samples differ")
}
metadata <- metadata[match(colnames(counts_all), sample_id)]
metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Yurong1"))]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]

keep <- rowSums(counts_all >= as.integer(config$primary_filter$minimum_count)) >=
  as.integer(config$primary_filter$minimum_libraries)
counts <- counts_all[keep, , drop = FALSE]
if (nrow(counts) != 19445L) {
  stop("Expected 19,445 genes in the confirmatory universe, observed ", nrow(counts))
}

legacy <- fread(args$legacy)
if (nrow(legacy) != 18L || anyDuplicated(legacy$gene_id)) {
  stop("Legacy input must contain exactly 18 unique genes")
}

# H1: independent genome-wide within-cultivar models.
within_results <- list()
for (cultivar_name in c("Guiwei", "Yurong1")) {
  cultivar_metadata <- droplevels(as.data.frame(metadata[cultivar == cultivar_name]))
  rownames(cultivar_metadata) <- cultivar_metadata$sample_id
  cultivar_counts <- counts[, rownames(cultivar_metadata), drop = FALSE]
  if (ncol(cultivar_counts) != 6L || length(unique(cultivar_metadata$treatment)) != 2L) {
    stop("Unexpected within-cultivar design for ", cultivar_name)
  }
  dds_cultivar <- DESeqDataSetFromMatrix(
    countData = round(cultivar_counts),
    colData = cultivar_metadata,
    design = ~ treatment
  )
  dds_cultivar <- DESeq(
    dds_cultivar,
    test = "Wald",
    quiet = TRUE,
    parallel = FALSE,
    minReplicatesForReplace = Inf
  )
  result <- as.data.table(
    results(
      dds_cultivar,
      contrast = c("treatment", "infected", "mock"),
      independentFiltering = FALSE,
      cooksCutoff = FALSE
    ),
    keep.rownames = "gene_id"
  )
  setnames(
    result,
    c("log2FoldChange", "lfcSE", "pvalue", "padj"),
    c("log2fc", "lfc_se", "p", "q")
  )
  result[, cultivar := cultivar_name]
  within_results[[cultivar_name]] <- result
}

within <- rbindlist(within_results, use.names = TRUE)
h1 <- merge(
  CJ(gene_id = legacy$gene_id, cultivar = c("Guiwei", "Yurong1"), unique = TRUE),
  legacy,
  by = "gene_id",
  all.x = TRUE,
  sort = FALSE
)
h1 <- merge(h1, within, by = c("gene_id", "cultivar"), all.x = TRUE, sort = FALSE)
h1[, q_lt_0_05 := as_flag(q < 0.05)]
h1[, absolute_log2fc_ge_log2_1_5 := as_flag(abs(log2fc) >= lfc_min)]
h1[, q_and_effect_pass := q_lt_0_05 & absolute_log2fc_ge_log2_1_5]
setorder(h1, gene_id, cultivar)
write_tsv(
  h1[, .(
    gene_id, legacy_annotation, cultivar, baseMean, log2fc, lfc_se, stat, p, q,
    q_lt_0_05, absolute_log2fc_ge_log2_1_5, q_and_effect_pass
  )],
  args$supplement_out
)

# H2: the same full interaction fit, tested against |beta| <= log2(1.5).
full_metadata <- as.data.frame(metadata)
rownames(full_metadata) <- full_metadata$sample_id
dds <- DESeqDataSetFromMatrix(
  countData = round(counts),
  colData = full_metadata,
  design = ~ cultivar + treatment + cultivar:treatment
)
dds <- DESeq(
  dds,
  test = "Wald",
  quiet = TRUE,
  parallel = FALSE,
  minReplicatesForReplace = Inf
)
coefficient_name <- "cultivarYurong1.treatmentinfected"
if (!coefficient_name %in% resultsNames(dds)) stop("Interaction coefficient not found")

composite <- as.data.table(
  results(
    dds,
    name = coefficient_name,
    lfcThreshold = lfc_min,
    altHypothesis = "greaterAbs",
    independentFiltering = FALSE,
    cooksCutoff = FALSE
  ),
  keep.rownames = "gene_id"
)
setnames(
  composite,
  c("log2FoldChange", "lfcSE", "pvalue", "padj"),
  c("composite_null_log2fc", "composite_null_lfc_se", "composite_null_p", "composite_null_q")
)
composite[, composite_null_pass := as_flag(composite_null_q < q_max)]

apeglm_result <- as.data.table(
  lfcShrink(
    dds,
    coef = coefficient_name,
    type = "apeglm",
    lfcThreshold = lfc_min,
    svalue = TRUE,
    quiet = TRUE,
    parallel = FALSE
  ),
  keep.rownames = "gene_id"
)
if (!"svalue" %in% names(apeglm_result)) stop("apeglm result did not contain s-values")
apeglm_result <- apeglm_result[, .(
  gene_id,
  apeglm_threshold_log2fc = log2FoldChange,
  apeglm_threshold_lfc_se = lfcSE,
  apeglm_fsos_svalue = svalue
)]
apeglm_result[, apeglm_fsos_svalue_lt_0_05 := as_flag(apeglm_fsos_svalue < 0.05)]

h2 <- merge(composite, apeglm_result, by = "gene_id", all.x = TRUE, sort = FALSE)
write_tsv(h2, args$sensitivity_out)

# Append H2 sensitivity columns to S3 without changing any frozen source column.
s3 <- fread(args$s3)
if (nrow(s3) != 19445L || anyDuplicated(s3$gene_id)) stop("Unexpected S3 universe")
if (!setequal(s3$gene_id, h2$gene_id)) stop("S3 and H2 gene universes differ")
h2_ordered <- h2[match(s3$gene_id, gene_id)]
new_columns <- c(
  "composite_null_log2fc", "composite_null_lfc_se", "composite_null_p",
  "composite_null_q", "composite_null_pass", "apeglm_threshold_log2fc",
  "apeglm_threshold_lfc_se", "apeglm_fsos_svalue", "apeglm_fsos_svalue_lt_0_05"
)
for (column in new_columns) set(s3, j = column, value = h2_ordered[[column]])
write_tsv(s3, args$s3)

robustness <- fread(args$robustness)
gene_robustness <- robustness[entity_type == "gene"]
sets <- list(
  statistical_262 = s3[statistical_discovery == TRUE, gene_id],
  qc_retained_206 = s3[primary_gene_status == "DISCOVERED", gene_id],
  edgeR_gate_19 = gene_robustness[statistical_method_pass == TRUE, gene_id],
  internally_robust_16 = gene_robustness[internal_robustness_status == "PASS", gene_id]
)
expected_sizes <- c(262L, 206L, 19L, 16L)
if (!identical(as.integer(lengths(sets)), expected_sizes)) {
  stop("Unexpected 262/206/19/16 hierarchy: ", paste(lengths(sets), collapse = "/"))
}

summary <- rbindlist(lapply(names(sets), function(label) {
  ids <- sets[[label]]
  data.table(
    hierarchy = label,
    input_count = length(ids),
    composite_null_q_lt_0_05 = h2[gene_id %in% ids, sum(composite_null_pass)],
    apeglm_fsos_svalue_lt_0_05 = h2[gene_id %in% ids, sum(apeglm_fsos_svalue_lt_0_05)]
  )
}))
write_tsv(summary, args$summary_out)

h1_counts <- h1[, .(
  legacy_genes = .N,
  q_lt_0_05 = sum(q_lt_0_05),
  q_and_effect = sum(q_and_effect_pass)
), by = cultivar]
write_tsv(h1_counts, file.path(args$workdir, "H1_legacy_audit_summary.tsv"))
writeLines(capture.output(sessionInfo()), file.path(args$workdir, "H1_H2_R_sessionInfo.txt"))

cat("H1 within-cultivar legacy audit\n")
print(h1_counts)
cat("\nH2 hierarchy survival\n")
print(summary)
