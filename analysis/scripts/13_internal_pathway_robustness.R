#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(edgeR)
  library(limma)
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
  names(fields) <- vapply(fields, `[[`, character(1), 1L)
  lapply(fields, function(x) unique(x[-c(1L, 2L)]))
}

empty_outputs <- function(outdir) {
  write_tsv(data.table(
    pathway = character(), NGenes = integer(), Direction = character(),
    PValue = numeric(), FDR = numeric()
  ), file.path(outdir, "camera.tsv"))
  write_tsv(data.table(
    pathway = character(), NGenes = integer(), Direction = character(),
    PValue = numeric(), FDR = numeric()
  ), file.path(outdir, "roast.tsv"))
  write_tsv(data.table(
    pathway = character(), removed_leading_edge_gene = character(),
    deletion_NES = numeric(), deletion_p = numeric(), deletion_q = numeric()
  ), file.path(outdir, "leading_edge_deletion.tsv"))
  write_tsv(data.table(
    pathway = character(), replicate = integer(), random_score = numeric()
  ), file.path(outdir, "matched_random_scores.tsv"))
  write_tsv(data.table(
    pathway = character(), primary_NES = numeric(),
    internal_pathway_robustness_status = character()
  ), file.path(outdir, "frozen_pathway_robustness.tsv"))
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "counts", "metadata", "decisions", "primary-genes", "gene-qc",
  "frozen-pathways", "gmt", "config", "operational-config", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))
config <- fromJSON(args$config, simplifyVector = TRUE)
operational <- fromJSON(args[["operational-config"]], simplifyVector = TRUE)
set.seed(as.integer(operational$matched_random_pathways$seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

frozen <- fread(args[["frozen-pathways"]])
if (!nrow(frozen)) {
  empty_outputs(args$outdir)
  writeLines(c(
    "# Internal pathway robustness", "",
    "- No pathway crossed the frozen primary discovery threshold.",
    "- Pathway robustness was therefore not applicable."
  ), file.path(args$outdir, "pathway_robustness_summary.md"))
  quit(save = "no", status = 0L)
}

count_table <- fread(args$counts, check.names = FALSE)
counts <- as.matrix(count_table[, -1L])
rownames(counts) <- count_table[[1L]]
storage.mode(counts) <- "numeric"
metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)[primary_status == "INCLUDE"]
metadata <- metadata[match(colnames(counts), sample_id)]
metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Yurong1"))]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
design <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
if (qr(design)$rank != ncol(design)) stop("Pathway design is not full rank")
interaction_column <- grep("cultivarYurong1:treatmentinfected", colnames(design), fixed = TRUE)
if (length(interaction_column) != 1L) stop("Interaction contrast is not unique")
contrast <- rep(0, ncol(design))
contrast[interaction_column] <- 1

primary <- fread(args[["primary-genes"]])
primary <- primary[is.finite(signed_wald_stat)]
stats <- primary$signed_wald_stat
names(stats) <- primary$gene_id
stats <- sort(stats, decreasing = TRUE)
pathways <- read_gmt(args$gmt)
minimum_size <- as.integer(config$pathway_collection$minimum_size)
maximum_size <- as.integer(config$pathway_collection$maximum_size)
eligible <- pathways[vapply(pathways, function(x) {
  size <- sum(unique(x) %in% names(stats))
  size >= minimum_size && size <= maximum_size
}, logical(1))]
if (!all(frozen$pathway %in% names(eligible))) {
  stop("A frozen pathway is absent from the fixed pathway universe")
}

# camera and roast use the expression matrix, fixed design, and interaction contrast.
keep <- rownames(counts) %in% names(stats)
dge <- DGEList(counts = counts[keep, , drop = FALSE])
dge <- calcNormFactors(dge)
voom_fit <- voom(dge, design, plot = FALSE)
frozen_sets <- eligible[frozen$pathway]
indices <- ids2indices(frozen_sets, rownames(voom_fit$E), remove.empty = TRUE)
if (length(indices) != nrow(frozen)) stop("A frozen set became empty for limma tests")
camera_result <- as.data.table(camera(
  voom_fit$E, indices, design = design, contrast = contrast, sort = FALSE
), keep.rownames = "pathway")
roast_result <- as.data.table(mroast(
  voom_fit$E, index = indices, design = design, contrast = contrast,
  set.statistic = "mean", nrot = 9999, adjust.method = "BH", sort = "none"
), keep.rownames = "pathway")
write_tsv(camera_result, file.path(args$outdir, "camera.tsv"))
write_tsv(roast_result, file.path(args$outdir, "roast.tsv"))

# Remove the leading-edge gene with the largest absolute primary statistic and
# rerun fgsea across the complete fixed pathway universe for multiplicity control.
modified <- eligible
removed <- data.table(pathway = frozen$pathway, removed_leading_edge_gene = NA_character_)
for (pathway_name in frozen$pathway) {
  leading <- strsplit(
    frozen[pathway == pathway_name, leading_edge_genes], ";", fixed = TRUE
  )[[1L]]
  leading <- intersect(leading, names(stats))
  if (length(leading)) {
    chosen <- leading[which.max(abs(stats[leading]))]
    modified[[pathway_name]] <- setdiff(modified[[pathway_name]], chosen)
    removed[pathway == pathway_name, removed_leading_edge_gene := chosen]
  }
}
deletion_fit <- fgseaMultilevel(
  pathways = modified,
  stats = stats,
  minSize = minimum_size,
  maxSize = maximum_size,
  eps = as.numeric(operational$pathway_discovery$fgsea_eps),
  nPermSimple = as.integer(operational$pathway_discovery$fgsea_simple_permutations)
)
deletion_fit <- as.data.table(deletion_fit)[, .(
  pathway, deletion_NES = NES, deletion_p = pval, deletion_q = padj
)]
deletion <- merge(removed, deletion_fit, by = "pathway", all.x = TRUE, sort = FALSE)
write_tsv(deletion, file.path(args$outdir, "leading_edge_deletion.tsv"))

# Expression- and exon-length-matched empirical sets.
gene_qc <- fread(args[["gene-qc"]])[, .(gene_id, union_exon_bases)]
universe <- merge(
  primary[, .(gene_id, signed_wald_stat, mean_normalized_expression = baseMean)],
  gene_qc,
  by = "gene_id", all = FALSE, sort = FALSE
)[is.finite(mean_normalized_expression) & union_exon_bases > 0]
bins <- as.integer(operational$matched_random_pathways$quantile_bins_each)
universe[, expression_bin := pmax(1L, pmin(
  bins, as.integer(ceiling(frank(mean_normalized_expression, ties.method = "average") / .N * bins))
))]
universe[, length_bin := pmax(1L, pmin(
  bins, as.integer(ceiling(frank(union_exon_bases, ties.method = "average") / .N * bins))
))]
universe[, match_bin := paste(expression_bin, length_bin, sep = "_")]
universe_stats <- universe$signed_wald_stat
names(universe_stats) <- universe$gene_id
sets <- as.integer(operational$matched_random_pathways$sets)
random_rows <- list()
matched_summary <- list()
for (pathway_name in frozen$pathway) {
  members <- intersect(unique(eligible[[pathway_name]]), universe$gene_id)
  member_data <- universe[gene_id %in% members]
  observed_score <- abs(mean(member_data$signed_wald_stat))
  requested <- member_data[, .N, by = match_bin]
  pools <- lapply(requested$match_bin, function(bin) {
    universe[match_bin == bin & !gene_id %in% members, gene_id]
  })
  names(pools) <- requested$match_bin
  sufficient <- all(lengths(pools) >= requested$N)
  random_scores <- rep(NA_real_, sets)
  if (sufficient) {
    for (replicate_index in seq_len(sets)) {
      sampled <- unlist(Map(
        function(pool, size) sample(pool, size = size, replace = FALSE),
        pools, requested$N
      ), use.names = FALSE)
      random_scores[replicate_index] <- abs(mean(universe_stats[sampled]))
    }
  }
  percentile <- if (sufficient) mean(random_scores < observed_score) else NA_real_
  random_rows[[pathway_name]] <- data.table(
    pathway = pathway_name,
    replicate = seq_len(sets),
    random_score = random_scores
  )
  matched_summary[[pathway_name]] <- data.table(
    pathway = pathway_name,
    matched_gene_count = length(members),
    observed_score = observed_score,
    random_score_95th_percentile = if (sufficient) quantile(
      random_scores, probs = 0.95, names = FALSE, type = 8
    ) else NA_real_,
    empirical_percentile = percentile,
    matched_random_status = if (sufficient) "COMPUTED" else "INSUFFICIENT_MATCH_POOL"
  )
}
random_table <- rbindlist(random_rows)
matched <- rbindlist(matched_summary)
write_tsv(random_table, file.path(args$outdir, "matched_random_scores.tsv"))
write_tsv(matched, file.path(args$outdir, "matched_random_summary.tsv"))

# Combine the independent internal sensitivity layers without an additive score.
robustness <- frozen[, .(pathway, primary_NES = NES, primary_q = padj)]
robustness <- merge(
  robustness,
  camera_result[, .(
    pathway, camera_direction = Direction, camera_p = PValue, camera_q = FDR
  )], by = "pathway", all.x = TRUE, sort = FALSE
)
robustness <- merge(
  robustness,
  roast_result[, .(
    pathway, roast_direction = Direction, roast_p = PValue, roast_q = FDR
  )], by = "pathway", all.x = TRUE, sort = FALSE
)
robustness <- merge(robustness, deletion, by = "pathway", all.x = TRUE, sort = FALSE)
robustness <- merge(robustness, matched, by = "pathway", all.x = TRUE, sort = FALSE)
robustness[, expected_limma_direction := fifelse(primary_NES > 0, "Up", "Down")]
robustness[, camera_direction_agreement := camera_direction == expected_limma_direction]
robustness[, roast_direction_agreement := roast_direction == expected_limma_direction]
robustness[, camera_pass := camera_direction_agreement & !is.na(camera_q) &
             camera_q < as.numeric(operational$internal_pathway_robustness$camera_q_max)]
robustness[, roast_pass := roast_direction_agreement & !is.na(roast_q) &
             roast_q < as.numeric(operational$internal_pathway_robustness$roast_q_max)]
robustness[, leading_edge_deletion_pass := !is.na(deletion_q) &
             deletion_q < as.numeric(
               operational$internal_pathway_robustness$leading_edge_deletion_q_max
             ) & sign(deletion_NES) == sign(primary_NES)]
robustness[, matched_random_pass := !is.na(empirical_percentile) &
             empirical_percentile >= as.numeric(
               operational$internal_pathway_robustness$require_matched_random_percentile
             )]
robustness[, internal_pathway_robustness_status := fifelse(
  camera_pass & roast_pass & leading_edge_deletion_pass & matched_random_pass,
  "PASS", "FAIL"
)]
write_tsv(robustness, file.path(args$outdir, "frozen_pathway_robustness.tsv"))
writeLines(c(
  "# Internal pathway robustness", "",
  sprintf("- Frozen primary pathways: %d", nrow(frozen)),
  sprintf("- Pathways passing camera, roast, leading-edge deletion, and matched-set gates: %d",
          sum(robustness$internal_pathway_robustness_status == "PASS")),
  "- These tests use only the discovery dataset and frozen pathway universe."
), file.path(args$outdir, "pathway_robustness_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "pathway_robustness_sessionInfo.txt"))
