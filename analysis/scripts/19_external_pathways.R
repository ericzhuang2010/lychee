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
  setNames(as.list(args[seq(2L, length(args), by = 2L)]), keys)
}

write_tsv <- function(x, path) {
  fwrite(as.data.table(x), path, sep = "\t", quote = FALSE, na = "NA")
}

read_gmt <- function(path) {
  fields <- strsplit(readLines(path, warn = FALSE), "\t", fixed = TRUE)
  if (!length(fields) || any(lengths(fields) < 3L)) stop("Malformed GMT")
  names(fields) <- vapply(fields, `[[`, character(1), 1L)
  lapply(fields, function(x) unique(x[-c(1L, 2L)]))
}

empty_outputs <- function(outdir, study, reason = "The frozen discovery pathway set is empty; the branch is not applicable.") {
  write_tsv(data.table(
    pathway = character(), camera_direction = character(), camera_p = numeric(), camera_q = numeric()
  ), file.path(outdir, "camera.tsv"))
  write_tsv(data.table(
    pathway = character(), roast_direction = character(), roast_p = numeric(), roast_q = numeric()
  ), file.path(outdir, "roast.tsv"))
  write_tsv(data.table(
    pathway = character(), fgsea_NES = numeric(), fgsea_p = numeric(), fgsea_q = numeric()
  ), file.path(outdir, "fgsea.tsv"))
  write_tsv(data.table(
    pathway = character(), removed_leading_edge_gene = character(),
    deletion_direction = character(), deletion_p = numeric(), deletion_q = numeric()
  ), file.path(outdir, "leading_edge_deletion.tsv"))
  write_tsv(data.table(
    pathway = character(), replicate = integer(), random_score = numeric()
  ), file.path(outdir, "matched_random_scores.tsv"))
  write_tsv(data.table(
    pathway = character(), empirical_percentile = numeric(), matched_random_status = character()
  ), file.path(outdir, "matched_random_summary.tsv"))
  write_tsv(data.table(
    study = character(), pathway = character(), external_pathway_status = character()
  ), file.path(outdir, "frozen_pathway_tests.tsv"))
  writeLines(c(
    paste0("# External frozen pathway evaluation: ", study), "",
    paste0("- ", reason)
  ), file.path(outdir, "external_pathway_summary.md"))
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "counts", "metadata", "decisions", "external-genes", "frozen-pathways",
  "frozen-pathway-genes", "gmt", "gene-qc", "discovery-config",
  "external-config", "study", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

study <- args$study
external_config <- fromJSON(args[["external-config"]], simplifyVector = TRUE)
discovery_config <- fromJSON(args[["discovery-config"]], simplifyVector = TRUE)
study_config <- external_config$studies[[study]]
if (is.null(study_config)) stop("Study absent from external config")
set.seed(20260718)
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

frozen <- fread(args[["frozen-pathways"]])
if (!nrow(frozen)) {
  empty_outputs(args$outdir, study)
  quit(save = "no", status = 0L)
}
if (anyDuplicated(frozen$pathway)) stop("Duplicate frozen pathways")

count_table <- fread(args$counts, check.names = FALSE)
counts <- as.matrix(count_table[, -1L])
rownames(counts) <- count_table[[1L]]
storage.mode(counts) <- "numeric"
metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)[primary_status == "INCLUDE"]
metadata <- metadata[match(intersect(colnames(counts), sample_id), sample_id)]
counts <- counts[, metadata$sample_id, drop = FALSE]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]

if (study == "PRJNA450886") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Heiye"))]
  metadata[, time := factor(as.character(time_h), levels = c("24", "6", "48"))]
  design <- model.matrix(~ cultivar * treatment * time, metadata)
  contrast_name <- "primary_24h"
  target_column <- "cultivarHeiye:treatmentinfected"
  contrast <- rep(0, ncol(design)); names(contrast) <- colnames(design)
  contrast[target_column] <- 1
} else if (study == "PRJNA922966") {
  metadata[, tissue := factor(tissue, levels = c("fruit", "leaf"))]
  design <- model.matrix(~ tissue + treatment + tissue:treatment, metadata)
  contrast_name <- "primary_leaf_infection"
  contrast <- rep(0, ncol(design)); names(contrast) <- colnames(design)
  contrast[c("treatmentinfected", "tissueleaf:treatmentinfected")] <- 1
} else if (study == "PRJNA1090613") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "SFZ_unresolved"))]
  design <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
  contrast_name <- "exploratory_interaction"
  contrast <- rep(0, ncol(design)); names(contrast) <- colnames(design)
  contrast["cultivarSFZ_unresolved:treatmentinfected"] <- 1
} else {
  stop("Unsupported study: ", study)
}
if (anyNA(contrast) || qr(design)$rank != ncol(design) || !any(contrast != 0)) {
  stop("External pathway contrast is invalid")
}

gene_results <- fread(args[["external-genes"]])[
  contrast == contrast_name & is.finite(external_signed_stat)
]
stats <- gene_results$external_signed_stat
names(stats) <- gene_results$gene_id
stats <- sort(stats, decreasing = TRUE)
if (length(stats) < 10L) stop("Too few external statistics")

pathways <- read_gmt(args$gmt)
if (!all(frozen$pathway %in% names(pathways))) stop("Frozen pathway missing from fixed GMT")
minimum_size <- as.integer(discovery_config$pathway_collection$minimum_size)
maximum_size <- as.integer(discovery_config$pathway_collection$maximum_size)
frozen_sets <- pathways[frozen$pathway]
mapped_sizes <- vapply(frozen_sets, function(x) sum(x %in% names(stats)), integer(1))
testable <- mapped_sizes >= minimum_size & mapped_sizes <= maximum_size
if (!any(testable)) {
  empty_outputs(
    args$outdir, study,
    "Frozen discovery pathways exist, but none passes the prespecified external mapped-size gate."
  )
  tests <- frozen[, .(
    study = study,
    pathway,
    mapped_external_genes = unname(mapped_sizes[pathway]),
    external_pathway_status = "not_testable",
    study_role = study_config$role,
    direct_replication = FALSE,
    can_promote_tier_a = FALSE
  )]
  write_tsv(tests, file.path(args$outdir, "frozen_pathway_tests.tsv"))
  writeLines(capture.output(sessionInfo()), file.path(args$outdir, "external_pathway_sessionInfo.txt"))
  quit(save = "no", status = 0L)
}

keep <- rownames(counts) %in% names(stats)
dge <- DGEList(counts = counts[keep, , drop = FALSE])
dge <- calcNormFactors(dge)
voom_fit <- voom(dge, design, plot = FALSE)
testable_sets <- frozen_sets[testable]
indices <- ids2indices(testable_sets, rownames(voom_fit$E), remove.empty = TRUE)
if (length(indices) != sum(testable)) stop("A testable frozen set became empty")

camera_result <- as.data.table(camera(
  voom_fit$E, indices, design = design, contrast = contrast, sort = FALSE
), keep.rownames = "pathway")
setnames(camera_result, c("Direction", "PValue", "FDR"),
         c("camera_direction", "camera_p", "camera_q"))
roast_result <- as.data.table(mroast(
  voom_fit$E, index = indices, design = design, contrast = contrast,
  set.statistic = "mean", nrot = 9999, adjust.method = "BH", sort = "none"
), keep.rownames = "pathway")
setnames(roast_result, c("Direction", "PValue", "FDR"),
         c("roast_direction", "roast_p", "roast_q"))
write_tsv(camera_result, file.path(args$outdir, "camera.tsv"))
write_tsv(roast_result, file.path(args$outdir, "roast.tsv"))

fg <- fgseaMultilevel(
  pathways = testable_sets,
  stats = stats,
  minSize = minimum_size,
  maxSize = maximum_size,
  eps = 0,
  nPermSimple = 10000
)
fg <- as.data.table(fg)
fg[, leadingEdge := NULL]
setnames(fg, c("NES", "pval", "padj"), c("fgsea_NES", "fgsea_p", "fgsea_q"))
write_tsv(fg, file.path(args$outdir, "fgsea.tsv"))

frozen_gene_statistics <- fread(args[["frozen-pathway-genes"]])
modified_sets <- testable_sets
removed <- rbindlist(lapply(names(testable_sets), function(pathway_name) {
  candidates <- frozen_gene_statistics[
    pathway == pathway_name & leading_edge == TRUE & gene_id %in% testable_sets[[pathway_name]]
  ]
  chosen <- if (nrow(candidates)) {
    candidates$gene_id[which.max(abs(candidates$signed_wald_stat))]
  } else {
    NA_character_
  }
  if (!is.na(chosen)) modified_sets[[pathway_name]] <<- setdiff(modified_sets[[pathway_name]], chosen)
  data.table(pathway = pathway_name, removed_leading_edge_gene = chosen)
}))
modified_indices <- ids2indices(modified_sets, rownames(voom_fit$E), remove.empty = TRUE)
deletion_result <- as.data.table(camera(
  voom_fit$E, modified_indices, design = design, contrast = contrast, sort = FALSE
), keep.rownames = "pathway")
setnames(deletion_result, c("Direction", "PValue", "FDR"),
         c("deletion_direction", "deletion_p", "deletion_q"))
deletion_result <- merge(removed, deletion_result, by = "pathway", all.x = TRUE, sort = FALSE)
write_tsv(deletion_result, file.path(args$outdir, "leading_edge_deletion.tsv"))

gene_qc <- fread(args[["gene-qc"]])[, .(gene_id, union_exon_bases)]
universe <- merge(
  gene_results[, .(
    gene_id, external_signed_stat,
    mean_normalized_expression = baseMean
  )],
  gene_qc,
  by = "gene_id", all = FALSE, sort = FALSE
)[is.finite(mean_normalized_expression) & union_exon_bases > 0]
bins <- as.integer(external_config$pathways$quantile_bins_each)
universe[, expression_bin := pmax(1L, pmin(
  bins, as.integer(ceiling(frank(mean_normalized_expression, ties.method = "average") / .N * bins))
))]
universe[, length_bin := pmax(1L, pmin(
  bins, as.integer(ceiling(frank(union_exon_bases, ties.method = "average") / .N * bins))
))]
universe[, match_bin := paste(expression_bin, length_bin, sep = "_")]
universe_stats <- universe$external_signed_stat
names(universe_stats) <- universe$gene_id
sets <- as.integer(external_config$pathways$matched_random_sets)
random_rows <- list()
matched_rows <- list()
for (pathway_name in names(testable_sets)) {
  members <- intersect(testable_sets[[pathway_name]], universe$gene_id)
  member_data <- universe[gene_id %in% members]
  observed_score <- abs(mean(member_data$external_signed_stat))
  requested <- member_data[, .N, by = match_bin]
  pools <- lapply(requested$match_bin, function(bin) {
    universe[match_bin == bin & !gene_id %in% members, gene_id]
  })
  sufficient <- nrow(member_data) >= minimum_size && all(lengths(pools) >= requested$N)
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
    pathway = pathway_name, replicate = seq_len(sets), random_score = random_scores
  )
  matched_rows[[pathway_name]] <- data.table(
    pathway = pathway_name,
    matched_gene_count = length(members),
    observed_score = observed_score,
    random_score_95th_percentile = if (sufficient) {
      quantile(random_scores, 0.95, names = FALSE, type = 8)
    } else NA_real_,
    empirical_percentile = percentile,
    matched_random_status = if (sufficient) "COMPUTED" else "INSUFFICIENT_MATCH_POOL"
  )
}
random_table <- rbindlist(random_rows)
matched <- rbindlist(matched_rows)
write_tsv(random_table, file.path(args$outdir, "matched_random_scores.tsv"))
write_tsv(matched, file.path(args$outdir, "matched_random_summary.tsv"))

tests <- frozen[, .(pathway, discovery_NES = NES, discovery_q = padj)]
tests[, mapped_external_genes := unname(mapped_sizes[pathway])]
tests <- merge(tests, camera_result, by = "pathway", all.x = TRUE, sort = FALSE)
tests <- merge(tests, roast_result, by = "pathway", all.x = TRUE, sort = FALSE)
tests <- merge(tests, fg[, .(pathway, fgsea_NES, fgsea_p, fgsea_q)],
               by = "pathway", all.x = TRUE, sort = FALSE)
tests <- merge(tests, deletion_result, by = "pathway", all.x = TRUE, sort = FALSE)
tests <- merge(tests, matched, by = "pathway", all.x = TRUE, sort = FALSE)
tests[, expected_direction := fifelse(discovery_NES > 0, "Up", "Down")]
tests[, `:=`(
  camera_direction_agrees = camera_direction == expected_direction,
  roast_direction_agrees = roast_direction == expected_direction,
  fgsea_direction_agrees = sign(fgsea_NES) == sign(discovery_NES),
  deletion_direction_agrees = deletion_direction == expected_direction
)]
tests[, `:=`(
  camera_pass = camera_direction_agrees & camera_q < as.numeric(external_config$pathways$bh_q_max),
  roast_sensitivity_pass = roast_direction_agrees & roast_q < as.numeric(external_config$pathways$bh_q_max),
  fgsea_sensitivity_pass = fgsea_direction_agrees & fgsea_q < as.numeric(external_config$pathways$bh_q_max),
  leading_edge_deletion_pass = deletion_direction_agrees &
    deletion_q < as.numeric(external_config$pathways$leading_edge_deletion_q_max),
  matched_random_pass = empirical_percentile >=
    as.numeric(external_config$pathways$matched_random_percentile_min)
)]
tests[, external_pathway_status := fcase(
  is.na(camera_q), "not_testable",
  camera_pass & roast_sensitivity_pass & fgsea_sensitivity_pass &
    leading_edge_deletion_pass & matched_random_pass, "cross_context_supported",
  default = "unsupported"
)]
tests[, `:=`(
  study = study,
  study_role = study_config$role,
  direct_replication = FALSE,
  can_promote_tier_a = study == "PRJNA450886"
)]
setorder(tests, camera_q, pathway, na.last = TRUE)
write_tsv(tests, file.path(args$outdir, "frozen_pathway_tests.tsv"))
writeLines(c(
  paste0("# External frozen pathway evaluation: ", study), "",
  sprintf("- Frozen pathways: %d", nrow(frozen)),
  sprintf("- Testable pathways: %d", sum(testable)),
  sprintf("- Pathways passing camera, roast, fgsea, deletion, and matched-null gates: %d",
          sum(tests$external_pathway_status == "cross_context_supported")),
  "- Membership and discovery direction were not re-estimated externally.",
  "- This is cross-context evidence, not direct replication."
), file.path(args$outdir, "external_pathway_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "external_pathway_sessionInfo.txt"))
