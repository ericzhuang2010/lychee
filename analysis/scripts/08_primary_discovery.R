#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DESeq2)
  library(apeglm)
  library(jsonlite)
  library(ggplot2)
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

assert_full_rank <- function(metadata) {
  matrix <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
  if (qr(matrix)$rank != ncol(matrix)) {
    stop("Primary design matrix is not full rank")
  }
  invisible(matrix)
}

run_wald <- function(counts, metadata, coefficient_name, independent_filtering = FALSE) {
  metadata <- as.data.frame(metadata)
  rownames(metadata) <- metadata$sample_id
  dds <- DESeqDataSetFromMatrix(
    countData = round(counts),
    colData = metadata,
    design = ~ cultivar + treatment + cultivar:treatment
  )
  dds <- DESeq(
    dds,
    test = "Wald",
    quiet = TRUE,
    parallel = FALSE,
    minReplicatesForReplace = Inf
  )
  if (!coefficient_name %in% resultsNames(dds)) {
    stop(
      "Locked interaction coefficient not found: ", coefficient_name,
      "; available: ", paste(resultsNames(dds), collapse = ", ")
    )
  }
  result <- results(
    dds,
    name = coefficient_name,
    independentFiltering = independent_filtering,
    cooksCutoff = FALSE
  )
  list(dds = dds, result = result)
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c("counts", "metadata", "decisions", "config", "legacy", "outdir")
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

config <- fromJSON(args$config, simplifyVector = TRUE)
set.seed(as.integer(config$random_seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)
dir.create("results/audit", recursive = TRUE, showWarnings = FALSE)

count_table <- fread(args$counts, check.names = FALSE)
if (names(count_table)[1] != "gene_id") stop("First count-matrix column must be gene_id")
if (anyDuplicated(count_table$gene_id)) stop("Count matrix contains duplicate gene IDs")
genes <- count_table$gene_id
counts <- as.matrix(count_table[, -1])
rownames(counts) <- genes
storage.mode(counts) <- "integer"
if (any(counts < 0L) || any(counts != round(counts))) stop("Counts must be nonnegative integers")

metadata <- fread(args$metadata)
decisions <- fread(args$decisions)
metadata <- merge(metadata, decisions, by = "sample_id", all.x = TRUE, sort = FALSE)
if (anyNA(metadata$primary_status)) stop("Missing preregistered sample decision")
if (!setequal(colnames(counts), metadata$sample_id)) {
  stop("Count matrix and metadata sample IDs differ")
}
metadata <- metadata[match(colnames(counts), sample_id)]
metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Yurong1"))]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
if (anyNA(metadata$cultivar) || anyNA(metadata$treatment)) {
  stop("Unexpected cultivar or treatment level")
}

primary_metadata <- metadata[primary_status == "INCLUDE"]
primary_counts_all_genes <- counts[, primary_metadata$sample_id, drop = FALSE]
cell_counts <- primary_metadata[, .N, by = .(cultivar, treatment)]
if (nrow(cell_counts) != 4L || any(cell_counts$N < 3L)) {
  stop("Primary data fail the locked >=3 libraries per cell gate")
}
model_matrix <- assert_full_rank(primary_metadata)
write_tsv(
  data.table(
    metric = c("samples", "genes_before_filter", "design_columns", "design_rank"),
    value = c(
      nrow(primary_metadata), nrow(primary_counts_all_genes),
      ncol(model_matrix), qr(model_matrix)$rank
    ),
    status = "PASS"
  ),
  file.path(args$outdir, "model_matrix_qc.tsv")
)

keep <- rowSums(primary_counts_all_genes >= as.integer(config$primary_filter$minimum_count)) >=
  as.integer(config$primary_filter$minimum_libraries)
if (!any(keep)) stop("No genes pass the locked primary expression filter")
filtered_counts <- primary_counts_all_genes[keep, , drop = FALSE]

coefficient_name <- "cultivarYurong1.treatmentinfected"
fit <- run_wald(filtered_counts, primary_metadata, coefficient_name)
dds <- fit$dds
interaction <- as.data.table(fit$result, keep.rownames = "gene_id")
setnames(
  interaction,
  c("log2FoldChange", "lfcSE", "pvalue", "padj"),
  c("interaction_log2fc", "interaction_lfc_se", "interaction_p", "interaction_q")
)
interaction[, signed_wald_stat := stat]

shrunken <- lfcShrink(dds, coef = coefficient_name, type = "apeglm")
shrunken_table <- as.data.table(shrunken, keep.rownames = "gene_id")[
  , .(gene_id, shrunken_interaction_log2fc = log2FoldChange)
]
interaction <- merge(interaction, shrunken_table, by = "gene_id", all.x = TRUE, sort = FALSE)
interaction[, statistical_discovery :=
  !is.na(interaction_q) &
  interaction_q < as.numeric(config$gene_discovery$bh_q_max) &
  abs(interaction_log2fc) >= as.numeric(config$gene_discovery$absolute_log2fc_min)
]
interaction[, mappability_status := "PENDING_UNIFORM_GENE_QC"]
interaction[, unique_gene_model_status := "PENDING_UNIFORM_GENE_QC"]
interaction[, primary_gene_status := "NOT_FROZEN_UNTIL_MAPPING_QC"]
setorder(interaction, interaction_p, gene_id, na.last = TRUE)
write_tsv(interaction, file.path(args$outdir, "all_genes_primary.tsv"))
write_tsv(
  interaction[statistical_discovery == TRUE],
  file.path(args$outdir, "statistical_candidates.tsv")
)

guiwei <- as.data.table(
  results(
    dds,
    contrast = c("treatment", "infected", "mock"),
    independentFiltering = FALSE,
    cooksCutoff = FALSE
  ),
  keep.rownames = "gene_id"
)
guiwei[, contrast := "infection_in_Guiwei"]
yurong <- as.data.table(
  results(
    dds,
    contrast = list(c("treatment_infected_vs_mock", coefficient_name)),
    independentFiltering = FALSE,
    cooksCutoff = FALSE
  ),
  keep.rownames = "gene_id"
)
yurong[, contrast := "infection_in_Yurong1"]
within <- rbindlist(list(guiwei, yurong), use.names = TRUE, fill = TRUE)
setnames(within, c("log2FoldChange", "lfcSE", "pvalue", "padj"),
         c("log2fc", "lfc_se", "p", "q"))
write_tsv(within, file.path(args$outdir, "within_cultivar_contrasts.tsv"))

dds_lrt <- DESeqDataSetFromMatrix(
  countData = filtered_counts,
  colData = {
    value <- as.data.frame(primary_metadata)
    rownames(value) <- value$sample_id
    value
  },
  design = ~ cultivar + treatment + cultivar:treatment
)
dds_lrt <- DESeq(
  dds_lrt,
  test = "LRT",
  reduced = ~ cultivar + treatment,
  quiet = TRUE,
  parallel = FALSE,
  minReplicatesForReplace = Inf
)
lrt <- as.data.table(
  results(dds_lrt, independentFiltering = FALSE, cooksCutoff = FALSE),
  keep.rownames = "gene_id"
)
setnames(lrt, c("log2FoldChange", "lfcSE", "pvalue", "padj"),
         c("lrt_model_log2fc", "lrt_lfc_se", "lrt_p", "lrt_q"))
write_tsv(lrt, file.path(args$outdir, "interaction_lrt.tsv"))

normalized <- as.data.table(counts(dds, normalized = TRUE), keep.rownames = "gene_id")
write_tsv(normalized, file.path(args$outdir, "normalized_counts.tsv"))
vst_object <- varianceStabilizingTransformation(dds, blind = FALSE)
vst_matrix <- assay(vst_object)
write_tsv(
  as.data.table(vst_matrix, keep.rownames = "gene_id"),
  file.path(args$outdir, "vst_expression.tsv")
)
sample_correlation <- cor(vst_matrix, method = "pearson")
write_tsv(
  as.data.table(sample_correlation, keep.rownames = "sample_id"),
  file.path(args$outdir, "sample_correlations.tsv")
)
sample_distances <- as.matrix(dist(t(vst_matrix)))
write_tsv(
  as.data.table(sample_distances, keep.rownames = "sample_id"),
  file.path(args$outdir, "sample_distances.tsv")
)

pca <- prcomp(t(vst_matrix), center = TRUE, scale. = FALSE)
pca_variance <- (pca$sdev^2) / sum(pca$sdev^2)
pca_table <- data.table(
  sample_id = rownames(pca$x),
  PC1 = pca$x[, 1],
  PC2 = pca$x[, 2]
)
pca_table <- merge(
  pca_table,
  primary_metadata[, .(sample_id, cultivar, treatment, replicate)],
  by = "sample_id",
  sort = FALSE
)
write_tsv(pca_table, file.path(args$outdir, "pca_samples.tsv"))
p <- ggplot(pca_table, aes(PC1, PC2, color = cultivar, shape = treatment, label = sample_id)) +
  geom_point(size = 3) +
  geom_text(nudge_y = 0.25, size = 2.5, show.legend = FALSE) +
  labs(
    x = sprintf("PC1 (%.1f%%)", 100 * pca_variance[1]),
    y = sprintf("PC2 (%.1f%%)", 100 * pca_variance[2])
  ) +
  theme_bw(base_size = 11)
ggsave(file.path(args$outdir, "pca_samples.pdf"), p, width = 6.5, height = 5)
ggsave(file.path(args$outdir, "pca_samples.png"), p, width = 6.5, height = 5, dpi = 300)

cooks <- assays(dds)[["cooks"]]
cooks_table <- data.table(
  gene_id = rownames(cooks),
  maximum_cooks_distance = apply(cooks, 1, max, na.rm = TRUE)
)
write_tsv(cooks_table, file.path(args$outdir, "maximum_cooks_distance.tsv"))

legacy <- fread(args$legacy)
legacy_audit <- merge(legacy, interaction, by = "gene_id", all.x = TRUE, sort = FALSE)
legacy_audit[, present_in_filtered_universe := !is.na(interaction_p)]
write_tsv(legacy_audit, file.path(args$outdir, "legacy_18_audit.tsv"))

if (nrow(primary_metadata) != nrow(metadata)) {
  all_model <- assert_full_rank(metadata)
  all_keep <- rowSums(counts >= as.integer(config$primary_filter$minimum_count)) >=
    as.integer(config$primary_filter$minimum_libraries)
  all_fit <- run_wald(counts[all_keep, , drop = FALSE], metadata, coefficient_name)
  all_sensitivity <- as.data.table(all_fit$result, keep.rownames = "gene_id")
  write_tsv(all_sensitivity, file.path(args$outdir, "all_sample_sensitivity.tsv"))
}

summary_lines <- c(
  "# Discovery statistical summary",
  "",
  sprintf("- Primary libraries: %d", nrow(primary_metadata)),
  sprintf("- Genes before filter: %d", nrow(primary_counts_all_genes)),
  sprintf("- Genes passing count >= 10 in >= 3 libraries: %d", sum(keep)),
  sprintf("- Statistical interaction candidates (q < 0.05 and |log2FC| >= log2(1.5)): %d",
          sum(interaction$statistical_discovery, na.rm = TRUE)),
  "- Candidate genes are not frozen until uniform mappability and gene-model QC are joined.",
  "- q values are model-based evidence conditional on deposited-library independence.",
  "- External outcomes remained closed during this analysis."
)
writeLines(summary_lines, file.path(args$outdir, "statistical_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "R_sessionInfo.txt"))
