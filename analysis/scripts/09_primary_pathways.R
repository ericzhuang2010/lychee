#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(fgsea)
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

read_gmt <- function(path) {
  fields <- strsplit(readLines(path, warn = FALSE), "\t", fixed = TRUE)
  if (!length(fields) || any(lengths(fields) < 3L)) stop("Malformed or empty GMT: ", path)
  names(fields) <- vapply(fields, `[[`, character(1), 1L)
  if (anyDuplicated(names(fields))) stop("Duplicate pathway names in GMT")
  lapply(fields, function(x) unique(x[-c(1L, 2L)]))
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c("genes", "gmt", "config", "operational-config", "outdir")
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

config <- fromJSON(args$config, simplifyVector = TRUE)
operational <- fromJSON(args[["operational-config"]], simplifyVector = TRUE)
set.seed(as.integer(config$random_seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

gene_results <- fread(args$genes)
required_gene_columns <- c("gene_id", "signed_wald_stat")
if (!all(required_gene_columns %in% names(gene_results))) {
  stop("Primary gene table lacks signed Wald statistics")
}
gene_results <- gene_results[is.finite(signed_wald_stat) & !is.na(gene_id)]
if (anyDuplicated(gene_results$gene_id)) stop("Duplicate genes in primary table")
stats <- gene_results$signed_wald_stat
names(stats) <- gene_results$gene_id
stats <- sort(stats, decreasing = TRUE)
if (length(stats) < 10L) stop("Too few finite gene statistics for pathway testing")

pathways <- read_gmt(args$gmt)
minimum_size <- as.integer(config$pathway_collection$minimum_size)
maximum_size <- as.integer(config$pathway_collection$maximum_size)
eligible <- pathways[
  vapply(pathways, function(x) {
    size <- sum(unique(x) %in% names(stats))
    size >= minimum_size && size <= maximum_size
  }, logical(1))
]
if (!length(eligible)) stop("No pathway passes the frozen mapped-size gate")

fg <- fgseaMultilevel(
  pathways = eligible,
  stats = stats,
  minSize = minimum_size,
  maxSize = maximum_size,
  eps = as.numeric(operational$pathway_discovery$fgsea_eps),
  nPermSimple = as.integer(operational$pathway_discovery$fgsea_simple_permutations)
)
fg <- as.data.table(fg)
fg[, leading_edge_genes := vapply(leadingEdge, paste, character(1), collapse = ";")]
fg[, leadingEdge := NULL]
fg[, members := vapply(pathway, function(p) {
  paste(sort(intersect(unique(eligible[[p]]), names(stats))), collapse = ";")
}, character(1))]
fg[, direction := fifelse(
  NES > 0,
  "stronger_infection_response_in_Yurong1",
  "stronger_infection_response_in_Guiwei"
)]
fg[, discovered_pathway := !is.na(padj) &
     padj < as.numeric(operational$pathway_discovery$bh_q_max)]
setorder(fg, padj, pval, pathway, na.last = TRUE)
write_tsv(fg, file.path(args$outdir, "all_pathways_primary.tsv"))

frozen <- fg[discovered_pathway == TRUE]
write_tsv(frozen, file.path(args$outdir, "frozen_pathways.tsv"))

if (nrow(frozen)) {
  long <- rbindlist(lapply(frozen$pathway, function(p) {
    members <- intersect(unique(eligible[[p]]), names(stats))
    data.table(
      pathway = p,
      gene_id = members,
      signed_wald_stat = unname(stats[members]),
      leading_edge = members %in% strsplit(
        frozen[pathway == p, leading_edge_genes], ";", fixed = TRUE
      )[[1L]]
    )
  }))
} else {
  long <- data.table(
    pathway = character(), gene_id = character(),
    signed_wald_stat = numeric(), leading_edge = logical()
  )
}
setorder(long, pathway, -signed_wald_stat, gene_id)
write_tsv(long, file.path(args$outdir, "frozen_pathway_gene_statistics.tsv"))

summary_lines <- c(
  "# Primary pathway discovery",
  "",
  sprintf("- Finite interaction statistics: %d", length(stats)),
  sprintf("- Frozen eligible pathways: %d", length(eligible)),
  sprintf("- Pathways at BH q < %.3g: %d",
          as.numeric(operational$pathway_discovery$bh_q_max), nrow(frozen)),
  "- Positive NES means a stronger infection response in Yurong1 than Guiwei.",
  "- External outcomes remained closed."
)
writeLines(summary_lines, file.path(args$outdir, "pathway_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "pathway_sessionInfo.txt"))
