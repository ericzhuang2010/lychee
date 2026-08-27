#!/usr/bin/env Rscript

parse_args <- function(args) {
  out <- list(seed = 20260718L, outdir = "analysis/tests/fixtures")
  index <- 1L
  while (index <= length(args)) {
    key <- args[[index]]
    if (!key %in% c("--seed", "--outdir") || index == length(args)) {
      stop("Usage: create_synthetic_fixture.R --seed N --outdir DIR")
    }
    out[[sub("^--", "", key)]] <- args[[index + 1L]]
    index <- index + 2L
  }
  out$seed <- as.integer(out$seed)
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
set.seed(args$seed)
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

metadata <- expand.grid(
  replicate = seq_len(3L),
  treatment = c("mock", "infected"),
  cultivar = c("Guiwei", "Yurong1"),
  KEEP.OUT.ATTRS = FALSE,
  stringsAsFactors = FALSE
)
metadata <- metadata[order(metadata$cultivar, metadata$treatment, metadata$replicate), ]
metadata$sample_id <- sprintf(
  "%s_%s_%d",
  ifelse(metadata$cultivar == "Guiwei", "GW", "YR"),
  ifelse(metadata$treatment == "mock", "M", "P"),
  metadata$replicate
)
metadata <- metadata[, c("sample_id", "cultivar", "treatment", "replicate")]

n_genes <- 200L
gene_id <- sprintf("gene_%03d", seq_len(n_genes))
baseline <- exp(runif(n_genes, log(150), log(1200)))
main_cultivar <- rep(log(1.15), n_genes)
main_treatment <- rep(log(1.25), n_genes)
interaction <- rep(0, n_genes)
interaction[1:8] <- log(8)
interaction[9:16] <- log(1 / 8)

counts <- matrix(0L, nrow = n_genes, ncol = nrow(metadata), dimnames = list(gene_id, metadata$sample_id))
for (column in seq_len(nrow(metadata))) {
  is_yurong <- metadata$cultivar[column] == "Yurong1"
  is_infected <- metadata$treatment[column] == "infected"
  mean_count <- baseline *
    exp(main_cultivar * is_yurong) *
    exp(main_treatment * is_infected) *
    exp(interaction * is_yurong * is_infected)
  counts[, column] <- rnbinom(n_genes, mu = mean_count, size = 80)
}

expected <- data.frame(
  gene_id = gene_id,
  expected_sign = c(rep("positive", 8), rep("negative", 8), rep("null", n_genes - 16)),
  expected_class = c(rep("interaction", 16), rep("null", n_genes - 16)),
  stringsAsFactors = FALSE
)

confounded <- metadata
confounded$cultivar <- rep(c("Guiwei", "Yurong1"), each = 6L)
confounded$treatment <- rep(c("mock", "infected"), each = 6L)

write.table(counts, file.path(args$outdir, "counts.tsv"), sep = "\t", quote = FALSE, col.names = NA)
write.table(metadata, file.path(args$outdir, "metadata.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
write.table(confounded, file.path(args$outdir, "metadata_confounded.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
write.table(expected, file.path(args$outdir, "expected_results.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
writeLines(as.character(args$seed), file.path(args$outdir, "seed.txt"))

