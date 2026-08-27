#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DESeq2)
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

coefficient <- function(names, pattern) {
  hit <- grep(pattern, names, value = TRUE)
  if (length(hit) != 1L) {
    stop("Expected one coefficient matching ", pattern, "; observed: ", paste(hit, collapse = ","))
  }
  hit
}

result_table <- function(dds, specification, contrast_name, estimand) {
  result <- if (length(specification) == 1L) {
    results(dds, name = specification, independentFiltering = FALSE, cooksCutoff = FALSE)
  } else {
    results(dds, contrast = list(specification), independentFiltering = FALSE, cooksCutoff = FALSE)
  }
  table <- as.data.table(result, keep.rownames = "gene_id")
  setnames(
    table,
    c("log2FoldChange", "lfcSE", "stat", "pvalue", "padj"),
    c("external_log2fc", "external_lfc_se", "external_signed_stat", "external_p", "genomewide_q")
  )
  table[, `:=`(contrast = contrast_name, estimand = estimand)]
  table
}

new_row <- function(...) as.data.frame(list(...), stringsAsFactors = FALSE)

lm_contrast <- function(fit, positive_rows, negative_rows, contrast_name, estimand) {
  terms_without_response <- delete.response(terms(fit))
  positive <- model.matrix(
    terms_without_response, positive_rows,
    contrasts.arg = fit$contrasts, xlev = fit$xlevels
  )
  negative <- model.matrix(
    terms_without_response, negative_rows,
    contrasts.arg = fit$contrasts, xlev = fit$xlevels
  )
  vector <- colSums(positive) - colSums(negative)
  vector <- vector[names(coef(fit))]
  estimate <- sum(vector * coef(fit))
  standard_error <- sqrt(as.numeric(t(vector) %*% vcov(fit) %*% vector))
  statistic <- estimate / standard_error
  p <- 2 * pt(abs(statistic), df = df.residual(fit), lower.tail = FALSE)
  data.table(
    contrast = contrast_name,
    estimand = estimand,
    estimate = estimate,
    standard_error = standard_error,
    confidence_lower = estimate - qt(0.975, df.residual(fit)) * standard_error,
    confidence_upper = estimate + qt(0.975, df.residual(fit)) * standard_error,
    statistic = statistic,
    degrees_freedom = df.residual(fit),
    p = p
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "counts", "metadata", "decisions", "frozen-genes", "frozen-signature",
  "config", "study", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

config <- fromJSON(args$config, simplifyVector = TRUE)
study <- args$study
study_config <- config$studies[[study]]
if (is.null(study_config)) stop("Study is absent from frozen external config: ", study)
set.seed(20260718)
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

count_table <- fread(args$counts, check.names = FALSE)
if (names(count_table)[1L] != "gene_id" || anyDuplicated(count_table$gene_id)) {
  stop("Invalid count matrix gene column")
}
counts <- as.matrix(count_table[, -1L])
rownames(counts) <- count_table$gene_id
storage.mode(counts) <- "integer"
metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)
if (anyNA(metadata$primary_status)) stop("Missing technical decision")
metadata <- metadata[primary_status == "INCLUDE"]
if (!all(metadata$sample_id %in% colnames(counts))) stop("Included sample absent from count matrix")
metadata <- metadata[match(intersect(colnames(counts), metadata$sample_id), sample_id)]
counts <- counts[, metadata$sample_id, drop = FALSE]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]

if (study == "PRJNA450886") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Heiye"))]
  metadata[, time := factor(as.character(time_h), levels = c("24", "6", "48"))]
  design_formula <- ~ cultivar * treatment * time
} else if (study == "PRJNA922966") {
  metadata[, tissue := factor(tissue, levels = c("fruit", "leaf"))]
  design_formula <- ~ tissue + treatment + tissue:treatment
} else if (study == "PRJNA1090613") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "SFZ_unresolved"))]
  design_formula <- ~ cultivar + treatment + cultivar:treatment
} else {
  stop("No external model implementation for ", study)
}
design <- model.matrix(design_formula, metadata)
if (anyNA(design) || qr(design)$rank != ncol(design)) stop("External design matrix is not full rank")

keep <- rowSums(counts >= as.integer(config$expression_filter$minimum_count)) >=
  as.integer(config$expression_filter$minimum_libraries)
if (!any(keep)) stop("No genes pass the frozen external expression filter")
filtered_counts <- counts[keep, , drop = FALSE]
col_data <- as.data.frame(metadata)
rownames(col_data) <- metadata$sample_id
dds <- DESeqDataSetFromMatrix(
  countData = filtered_counts,
  colData = col_data,
  design = design_formula
)
dds <- DESeq(dds, quiet = TRUE, parallel = FALSE, minReplicatesForReplace = Inf)
available <- resultsNames(dds)
write_tsv(
  as.data.table(counts(dds, normalized = TRUE), keep.rownames = "gene_id"),
  file.path(args$outdir, "normalized_counts.tsv")
)

if (study == "PRJNA450886") {
  base <- coefficient(available, "^cultivarHeiye\\.treatmentinfected$")
  triple6 <- coefficient(available, "^cultivarHeiye\\.treatmentinfected\\.time6$")
  triple48 <- coefficient(available, "^cultivarHeiye\\.treatmentinfected\\.time48$")
  contrast_specs <- list(
    primary_24h = base,
    secondary_6h = c(base, triple6),
    secondary_48h = c(base, triple48)
  )
  estimands <- c(
    primary_24h = "resistant-minus-susceptible cultivar-by-infection at 24 h",
    secondary_6h = "resistant-minus-susceptible cultivar-by-infection at 6 h",
    secondary_48h = "resistant-minus-susceptible cultivar-by-infection at 48 h"
  )
  primary_contrast <- "primary_24h"
} else if (study == "PRJNA922966") {
  infection <- coefficient(available, "^treatment_infected_vs_mock$")
  interaction <- coefficient(available, "^tissueleaf\\.treatmentinfected$")
  contrast_specs <- list(
    primary_leaf_infection = c(infection, interaction),
    secondary_fruit_infection = infection,
    secondary_tissue_interaction = interaction
  )
  estimands <- c(
    primary_leaf_infection = "infected-minus-mock in Feizixiao leaf",
    secondary_fruit_infection = "infected-minus-mock in Feizixiao fruit",
    secondary_tissue_interaction = "leaf-minus-fruit infection interaction"
  )
  primary_contrast <- "primary_leaf_infection"
} else {
  interaction <- coefficient(available, "^cultivarSFZ_unresolved\\.treatmentinfected$")
  contrast_specs <- list(exploratory_interaction = interaction)
  estimands <- c(exploratory_interaction = "unstandardized unresolved-SFZ-group-minus-Guiwei infection interaction")
  primary_contrast <- "exploratory_interaction"
}

all_tests <- rbindlist(Map(
  function(specification, contrast_name) {
    result_table(dds, specification, contrast_name, estimands[[contrast_name]])
  },
  contrast_specs,
  names(contrast_specs)
), use.names = TRUE, fill = TRUE)
setorder(all_tests, contrast, external_p, gene_id, na.last = TRUE)
write_tsv(all_tests, file.path(args$outdir, "all_gene_contrasts.tsv"))

frozen <- fread(args[["frozen-genes"]])
frozen_core <- if (nrow(frozen)) {
  frozen[, .(
    gene_id,
    discovery_interaction_log2fc = interaction_log2fc,
    discovery_q = interaction_q,
    discovery_mappability_status = uniform_gene_qc_status
  )]
} else {
  data.table(
    gene_id = character(), discovery_interaction_log2fc = numeric(),
    discovery_q = numeric(), discovery_mappability_status = character()
  )
}
frozen_tests <- merge(
  CJ(gene_id = frozen_core$gene_id, contrast = names(contrast_specs), unique = TRUE),
  all_tests,
  by = c("gene_id", "contrast"), all.x = TRUE, sort = FALSE
)
frozen_tests <- merge(frozen_tests, frozen_core, by = "gene_id", all.x = TRUE, sort = FALSE)
frozen_tests[, external_q := {
  value <- rep(NA_real_, .N)
  finite <- is.finite(external_p)
  value[finite] <- p.adjust(external_p[finite], method = "BH")
  value
}, by = contrast]
z_value <- qnorm(0.5 + as.numeric(config$gene_support$confidence_level) / 2)
frozen_tests[, `:=`(
  confidence_lower = external_log2fc - z_value * external_lfc_se,
  confidence_upper = external_log2fc + z_value * external_lfc_se,
  measurable = is.finite(external_log2fc) & is.finite(external_lfc_se) & is.finite(external_p),
  direction_agrees = is.finite(external_log2fc) &
    sign(external_log2fc) == sign(discovery_interaction_log2fc)
)]
frozen_tests[, confidence_excludes_zero := measurable &
  (confidence_lower > 0 | confidence_upper < 0)]
frozen_tests[, threshold_pass := measurable &
  external_q < as.numeric(config$gene_support$bh_q_max) &
  abs(external_log2fc) >= as.numeric(config$gene_support$absolute_log2fc_min) &
  confidence_excludes_zero]
frozen_tests[, confirmatory_eligible := study == "PRJNA450886" & contrast == primary_contrast]
frozen_tests[, external_status := fcase(
  !measurable, "not_testable",
  !confirmatory_eligible, "not_testable",
  threshold_pass & direction_agrees, "cross_context_supported",
  threshold_pass & !direction_agrees, "contradictory",
  default = "unsupported"
)]
frozen_tests[, `:=`(
  study = study,
  study_role = study_config$role,
  direct_replication = FALSE,
  can_promote_tier_a = study == "PRJNA450886" & contrast == primary_contrast
)]
setorder(frozen_tests, contrast, external_q, gene_id, na.last = TRUE)
write_tsv(frozen_tests, file.path(args$outdir, "frozen_gene_tests.tsv"))

if (study == "PRJNA450886") {
  lrt_dds <- DESeqDataSetFromMatrix(
    countData = filtered_counts,
    colData = col_data,
    design = design_formula
  )
  lrt_dds <- DESeq(
    lrt_dds,
    test = "LRT",
    reduced = ~ cultivar * treatment + cultivar * time + treatment * time,
    quiet = TRUE,
    parallel = FALSE,
    minReplicatesForReplace = Inf
  )
  global <- as.data.table(
    results(lrt_dds, independentFiltering = FALSE, cooksCutoff = FALSE),
    keep.rownames = "gene_id"
  )
  setnames(global, c("stat", "pvalue", "padj"), c("three_way_lrt_stat", "three_way_lrt_p", "three_way_lrt_q"))
} else {
  global <- data.table(
    gene_id = character(), three_way_lrt_stat = numeric(),
    three_way_lrt_p = numeric(), three_way_lrt_q = numeric()
  )
}
write_tsv(global, file.path(args$outdir, "global_model_tests.tsv"))

vst <- varianceStabilizingTransformation(dds, blind = FALSE)
vst_matrix <- assay(vst)
write_tsv(as.data.table(vst_matrix, keep.rownames = "gene_id"), file.path(args$outdir, "vst_expression.tsv"))
pca <- prcomp(t(vst_matrix), center = TRUE, scale. = FALSE)
pca_variance <- pca$sdev^2 / sum(pca$sdev^2)
pca_table <- data.table(
  sample_id = rownames(pca$x), PC1 = pca$x[, 1L], PC2 = pca$x[, 2L],
  PC1_variance_fraction = pca_variance[1L], PC2_variance_fraction = pca_variance[2L]
)
pca_table <- merge(pca_table, metadata, by = "sample_id", sort = FALSE)
write_tsv(pca_table, file.path(args$outdir, "pca_samples.tsv"))

signature <- fread(args[["frozen-signature"]])
measurable_signature <- signature[gene_id %in% rownames(vst_matrix) & is.finite(weight)]
measurable_fraction <- if (nrow(signature)) nrow(measurable_signature) / nrow(signature) else 0
signature_valid <- nrow(signature) > 0L &&
  measurable_fraction >= as.numeric(config$signature$minimum_measurable_fraction) &&
  sum(abs(measurable_signature$weight)) > 0
if (signature_valid) {
  expression <- vst_matrix[measurable_signature$gene_id, , drop = FALSE]
  z_expression <- t(scale(t(expression)))
  score <- colSums(z_expression * measurable_signature$weight) /
    sum(abs(measurable_signature$weight))
  signature_samples <- data.table(sample_id = names(score), signature_score = unname(score))
  signature_samples <- merge(signature_samples, metadata, by = "sample_id", sort = FALSE)
  if (study == "PRJNA450886") {
    fit <- lm(signature_score ~ cultivar * treatment * time, data = signature_samples)
    signature_tests <- rbindlist(list(
      lm_contrast(
        fit,
        rbind(new_row(cultivar = "Heiye", treatment = "infected", time = "24"),
              new_row(cultivar = "Guiwei", treatment = "mock", time = "24")),
        rbind(new_row(cultivar = "Heiye", treatment = "mock", time = "24"),
              new_row(cultivar = "Guiwei", treatment = "infected", time = "24")),
        "primary_24h", estimands[["primary_24h"]]
      ),
      lm_contrast(
        fit,
        rbind(new_row(cultivar = "Heiye", treatment = "infected", time = "6"),
              new_row(cultivar = "Guiwei", treatment = "mock", time = "6")),
        rbind(new_row(cultivar = "Heiye", treatment = "mock", time = "6"),
              new_row(cultivar = "Guiwei", treatment = "infected", time = "6")),
        "secondary_6h", estimands[["secondary_6h"]]
      ),
      lm_contrast(
        fit,
        rbind(new_row(cultivar = "Heiye", treatment = "infected", time = "48"),
              new_row(cultivar = "Guiwei", treatment = "mock", time = "48")),
        rbind(new_row(cultivar = "Heiye", treatment = "mock", time = "48"),
              new_row(cultivar = "Guiwei", treatment = "infected", time = "48")),
        "secondary_48h", estimands[["secondary_48h"]]
      )
    ))
  } else if (study == "PRJNA922966") {
    fit <- lm(signature_score ~ tissue + treatment + tissue:treatment, data = signature_samples)
    signature_tests <- rbindlist(list(
      lm_contrast(
        fit, new_row(tissue = "leaf", treatment = "infected"),
        new_row(tissue = "leaf", treatment = "mock"),
        "primary_leaf_infection", estimands[["primary_leaf_infection"]]
      ),
      lm_contrast(
        fit, new_row(tissue = "fruit", treatment = "infected"),
        new_row(tissue = "fruit", treatment = "mock"),
        "secondary_fruit_infection", estimands[["secondary_fruit_infection"]]
      ),
      lm_contrast(
        fit,
        rbind(new_row(tissue = "leaf", treatment = "infected"),
              new_row(tissue = "fruit", treatment = "mock")),
        rbind(new_row(tissue = "leaf", treatment = "mock"),
              new_row(tissue = "fruit", treatment = "infected")),
        "secondary_tissue_interaction", estimands[["secondary_tissue_interaction"]]
      )
    ))
  } else {
    fit <- lm(signature_score ~ cultivar + treatment + cultivar:treatment, data = signature_samples)
    signature_tests <- lm_contrast(
      fit,
      rbind(new_row(cultivar = "SFZ_unresolved", treatment = "infected"),
            new_row(cultivar = "Guiwei", treatment = "mock")),
      rbind(new_row(cultivar = "SFZ_unresolved", treatment = "mock"),
            new_row(cultivar = "Guiwei", treatment = "infected")),
      "exploratory_interaction", estimands[["exploratory_interaction"]]
    )
  }
  signature_tests[, q := p.adjust(p, method = "BH")]
  signature_tests[, `:=`(
    study = study,
    study_role = study_config$role,
    measurable_fraction = measurable_fraction,
    frozen_gene_count = nrow(signature),
    measurable_gene_count = nrow(measurable_signature),
    direction_agrees = if (study == "PRJNA1090613") rep(NA, .N) else estimate > 0
  )]
  signature_groups <- signature_samples[, .(
    n = .N,
    mean_score = mean(signature_score),
    standard_error = sd(signature_score) / sqrt(.N),
    confidence_lower = mean(signature_score) - qt(0.975, .N - 1L) * sd(signature_score) / sqrt(.N),
    confidence_upper = mean(signature_score) + qt(0.975, .N - 1L) * sd(signature_score) / sqrt(.N)
  ), by = intersect(c("cultivar", "tissue", "treatment", "time"), names(signature_samples))]
} else {
  signature_samples <- data.table(sample_id = character(), signature_score = numeric())
  signature_tests <- data.table(
    contrast = character(), estimand = character(), estimate = numeric(),
    standard_error = numeric(), confidence_lower = numeric(), confidence_upper = numeric(),
    statistic = numeric(), degrees_freedom = numeric(), p = numeric(), q = numeric(),
    study = character(), study_role = character(), measurable_fraction = numeric(),
    frozen_gene_count = integer(), measurable_gene_count = integer(), direction_agrees = logical()
  )
  signature_groups <- data.table(group = character(), n = integer(), mean_score = numeric())
}
write_tsv(signature_samples, file.path(args$outdir, "signature_sample_scores.tsv"))
write_tsv(signature_groups, file.path(args$outdir, "signature_group_scores.tsv"))
write_tsv(signature_tests, file.path(args$outdir, "signature_contrasts.tsv"))

writeLines(c(
  paste0("# External frozen evaluation: ", study),
  "",
  sprintf("- Study role: %s", study_config$role),
  sprintf("- Included libraries after technical gates: %d", nrow(metadata)),
  sprintf("- Genes passing the frozen expression filter: %d", sum(keep)),
  sprintf("- Frozen discovery genes: %d", nrow(frozen)),
  sprintf("- Confirmatory cross-context-supported genes: %d",
          sum(frozen_tests$external_status == "cross_context_supported")),
  sprintf("- Contradictory genes: %d", sum(frozen_tests$external_status == "contradictory")),
  sprintf("- Frozen signature measurable fraction: %.3f", measurable_fraction),
  "- No external result was used to redefine frozen membership or weights.",
  "- No eligible external study is labeled a direct replication."
), file.path(args$outdir, "external_gene_signature_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "external_sessionInfo.txt"))
