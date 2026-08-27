#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(edgeR))
source("analysis/scripts/lib_metadata.R")

parse_args <- function(args) {
  out <- list(fixture = "analysis/tests/fixtures", expected = "analysis/tests/fixtures/expected_results.tsv")
  index <- 1L
  while (index <= length(args)) {
    key <- args[[index]]
    if (!key %in% c("--fixture", "--expected") || index == length(args)) {
      stop("Usage: test_interaction_pipeline.R --fixture DIR --expected FILE")
    }
    out[[sub("^--", "", key)]] <- args[[index + 1L]]
    index <- index + 2L
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
counts <- as.matrix(read.delim(file.path(args$fixture, "counts.tsv"), row.names = 1, check.names = FALSE))
metadata <- read.delim(file.path(args$fixture, "metadata.tsv"), check.names = FALSE)
expected <- read.delim(args$expected, check.names = FALSE)
metadata <- metadata[match(colnames(counts), metadata$sample_id), ]
stopifnot(identical(metadata$sample_id, colnames(counts)))
metadata$cultivar <- relevel(factor(metadata$cultivar), "Guiwei")
metadata$treatment <- relevel(factor(metadata$treatment), "mock")

formula <- ~ cultivar + treatment + cultivar:treatment
design <- validate_design(metadata, formula)
interaction_column <- grep("cultivarYurong1:treatmentinfected", colnames(design), fixed = TRUE)
if (length(interaction_column) != 1L) stop("Could not resolve the interaction coefficient")

dge <- DGEList(counts = counts)
dge <- calcNormFactors(dge)
dge <- estimateDisp(dge, design, robust = TRUE)
fit <- glmQLFit(dge, design, robust = TRUE)
test <- glmQLFTest(fit, coef = interaction_column)
result <- topTags(test, n = Inf, sort.by = "none")$table
result$gene_id <- rownames(result)
result <- result[match(expected$gene_id, result$gene_id), ]
result$expected_sign <- expected$expected_sign
result$expected_class <- expected$expected_class

positive <- result[result$expected_sign == "positive", ]
negative <- result[result$expected_sign == "negative", ]
null <- result[result$expected_sign == "null", ]
if (!all(positive$logFC > 0)) stop("Synthetic positive interactions did not retain their expected signs")
if (!all(negative$logFC < 0)) stop("Synthetic negative interactions did not retain their expected signs")
if (max(c(positive$FDR, negative$FDR)) >= median(null$FDR)) {
  stop("Synthetic interaction q-value ordering failed")
}
if (sum(c(positive$FDR, negative$FDR) < 0.05) < 14L) {
  stop("Fewer than 14/16 strong synthetic interactions passed FDR < 0.05")
}

confounded <- read.delim(file.path(args$fixture, "metadata_confounded.tsv"), check.names = FALSE)
confounded$cultivar <- factor(confounded$cultivar)
confounded$treatment <- factor(confounded$treatment)
rejected <- inherits(try(validate_design(confounded, formula), silent = TRUE), "try-error")
if (!rejected) stop("Confounded metadata were not rejected")

write.table(
  result[, c("gene_id", "logFC", "F", "PValue", "FDR", "expected_sign", "expected_class")],
  file.path(args$fixture, "observed_results.tsv"),
  sep = "\t", quote = FALSE, row.names = FALSE
)
writeLines(
  c(
    "PASS",
    sprintf("strong_interactions_fdr_lt_0.05=%d/16", sum(c(positive$FDR, negative$FDR) < 0.05)),
    sprintf("max_signal_fdr=%.6g", max(c(positive$FDR, negative$FDR))),
    sprintf("median_null_fdr=%.6g", median(null$FDR)),
    "confounded_metadata_rejected=true"
  ),
  file.path(args$fixture, "test_summary.txt")
)
message("Synthetic interaction gate passed")

