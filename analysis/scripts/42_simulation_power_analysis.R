#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DESeq2)
  library(ggplot2)
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

read_counts <- function(path) {
  tab <- fread(path, check.names = FALSE)
  if (names(tab)[1L] != "gene_id" || anyDuplicated(tab$gene_id)) stop("Invalid count table: ", path)
  mat <- as.matrix(tab[, -1L])
  rownames(mat) <- tab$gene_id
  storage.mode(mat) <- "integer"
  mat
}

load_metadata <- function(metadata_path, decisions_path, samples) {
  metadata <- merge(
    fread(metadata_path), fread(decisions_path),
    by = "sample_id", all.x = TRUE, sort = FALSE
  )
  if (anyNA(metadata$primary_status)) stop("Missing sample decision")
  metadata <- metadata[primary_status == "INCLUDE"]
  if (!all(samples %in% metadata$sample_id)) stop("Count sample absent from included metadata")
  metadata[match(samples, sample_id)]
}

prepare_fit <- function(counts, metadata, cultivar_levels, label, family_genes = NULL) {
  metadata <- copy(metadata)
  metadata[, cultivar := factor(cultivar, levels = cultivar_levels)]
  metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
  if (anyNA(metadata$cultivar) || anyNA(metadata$treatment)) stop("Unexpected factor level in ", label)
  design_formula <- ~ cultivar + treatment + cultivar:treatment
  design_matrix <- model.matrix(design_formula, metadata)
  if (qr(design_matrix)$rank != ncol(design_matrix)) stop("Rank-deficient design in ", label)
  keep <- rowSums(counts >= 10L) >= 3L
  counts <- counts[keep, , drop = FALSE]
  col_data <- as.data.frame(metadata)
  rownames(col_data) <- metadata$sample_id
  dds <- DESeqDataSetFromMatrix(countData = counts, colData = col_data, design = design_formula)
  dds <- DESeq(dds, quiet = TRUE, parallel = FALSE, minReplicatesForReplace = Inf)
  coefficient_name <- grep("cultivar.*treatmentinfected", resultsNames(dds), value = TRUE)
  if (length(coefficient_name) != 1L) {
    stop("Could not identify interaction coefficient in ", label, ": ", paste(resultsNames(dds), collapse = ", "))
  }
  coefficients <- coef(dds)
  if (!coefficient_name %in% colnames(coefficients)) {
    stop("Interaction coefficient absent from coefficient matrix in ", label)
  }
  fitted_mu <- assays(dds)[["mu"]]
  interaction_indicator <- as.numeric(metadata$cultivar == cultivar_levels[2L] & metadata$treatment == "infected")
  beta <- coefficients[, coefficient_name]
  mu_null <- fitted_mu / (2 ^ outer(beta, interaction_indicator))
  dispersion <- dispersions(dds)
  valid <- is.finite(dispersion) & dispersion > 0 & is.finite(beta) & apply(mu_null, 1L, function(x) all(is.finite(x) & x >= 0))
  if (!is.null(family_genes)) valid <- valid & rownames(dds) %in% family_genes
  dds <- dds[valid, ]
  mu_null <- mu_null[valid, , drop = FALSE]
  dispersion <- dispersion[valid]
  normalized_mean <- rowMeans(DESeq2::counts(dds, normalized = TRUE))
  expression_quartile <- cut(
    normalized_mean,
    breaks = unique(quantile(normalized_mean, probs = seq(0, 1, 0.25), na.rm = TRUE)),
    include.lowest = TRUE, labels = FALSE
  )
  if (anyNA(expression_quartile) || length(unique(expression_quartile)) != 4L) {
    expression_quartile <- as.integer(cut(rank(normalized_mean, ties.method = "first"), breaks = 4L, labels = FALSE))
  }
  names(expression_quartile) <- rownames(dds)
  list(
    label = label,
    dds = dds,
    col_data = col_data,
    design_formula = design_formula,
    coefficient_name = coefficient_name,
    mu_null = mu_null,
    dispersion = dispersion,
    size_factors = sizeFactors(dds),
    normalized_mean = normalized_mean,
    expression_quartile = expression_quartile,
    genes = rownames(dds)
  )
}

sample_targets <- function(fit, number) {
  sample(seq_along(fit$genes), number, replace = FALSE)
}

simulate_once <- function(fit, effect, iteration, target_number, threshold, seed, require_direction) {
  set.seed(seed)
  target <- sample_targets(fit, target_number)
  target_sign <- sample(c(-1, 1), length(target), replace = TRUE)
  true_effect <- target_sign * effect
  mu <- fit$mu_null
  indicator <- as.numeric(fit$col_data$cultivar == levels(fit$col_data$cultivar)[2L] & fit$col_data$treatment == "infected")
  mu[target, ] <- mu[target, , drop = FALSE] * (2 ^ outer(true_effect, indicator))
  mu <- pmax(mu, 1e-8)
  simulated <- matrix(
    rnbinom(length(mu), mu = as.vector(mu), size = rep(1 / fit$dispersion, times = ncol(mu))),
    nrow = nrow(mu), ncol = ncol(mu), dimnames = dimnames(mu)
  )
  storage.mode(simulated) <- "integer"
  dds <- DESeqDataSetFromMatrix(
    countData = simulated,
    colData = fit$col_data,
    design = fit$design_formula
  )
  sizeFactors(dds) <- fit$size_factors
  dispersions(dds) <- fit$dispersion
  dds <- nbinomWaldTest(dds, betaPrior = FALSE, quiet = TRUE)
  result <- results(
    dds, name = fit$coefficient_name,
    independentFiltering = FALSE, cooksCutoff = FALSE
  )
  estimate <- result$log2FoldChange[target]
  se <- result$lfcSE[target]
  p_value <- result$pvalue
  q_value <- rep(NA_real_, length(p_value))
  finite <- is.finite(p_value)
  q_value[finite] <- p.adjust(p_value[finite], method = "BH")
  target_q <- q_value[target]
  threshold_pass <- is.finite(target_q) & target_q < 0.05 & is.finite(estimate) & abs(estimate) >= threshold
  direction_pass <- if (effect == 0) rep(TRUE, length(target)) else sign(estimate) == sign(true_effect)
  ci_lower <- estimate - qnorm(0.975) * se
  ci_upper <- estimate + qnorm(0.975) * se
  ci_pass <- if (effect == 0) {
    rep(TRUE, length(target))
  } else {
    (true_effect > 0 & ci_lower > 0) | (true_effect < 0 & ci_upper < 0)
  }
  detected <- threshold_pass & (!require_direction | (direction_pass & ci_pass))
  data.table(
    design = fit$label,
    interaction_log2fc = effect,
    iteration = iteration,
    gene_id = fit$genes[target],
    expression_quartile = paste0("Q", fit$expression_quartile[target]),
    normalized_mean = fit$normalized_mean[target],
    true_effect = true_effect,
    estimated_effect = estimate,
    lfc_se = se,
    q_value = target_q,
    detected = detected
  )
}

wilson_interval <- function(successes, trials, confidence = 0.95) {
  if (trials == 0L) return(c(NA_real_, NA_real_))
  z <- qnorm(0.5 + confidence / 2)
  p <- successes / trials
  denominator <- 1 + z^2 / trials
  center <- (p + z^2 / (2 * trials)) / denominator
  half <- z * sqrt(p * (1 - p) / trials + z^2 / (4 * trials^2)) / denominator
  c(max(0, center - half), min(1, center + half))
}

summarize_power <- function(raw) {
  overall <- raw[, .(targets = .N, detected = sum(detected)), by = .(design, interaction_log2fc)][, expression_quartile := "Overall"]
  strata <- raw[, .(targets = .N, detected = sum(detected)), by = .(design, interaction_log2fc, expression_quartile)]
  summary <- rbindlist(list(overall, strata), use.names = TRUE)
  summary[, power := detected / targets]
  intervals <- t(mapply(wilson_interval, summary$detected, summary$targets))
  summary[, `:=`(ci_lower = intervals[, 1L], ci_upper = intervals[, 2L])]
  setorder(summary, design, expression_quartile, interaction_log2fc)
  summary
}

minimum_detectable <- function(summary) {
  summary[, {
    ordered <- .SD[order(interaction_log2fc)]
    at_or_above <- which(ordered$power >= 0.80)
    if (!length(at_or_above)) {
      value <- NA_real_
      status <- paste0(">", max(ordered$interaction_log2fc))
    } else if (at_or_above[1L] == 1L) {
      value <- ordered$interaction_log2fc[1L]
      status <- "estimated"
    } else {
      high <- at_or_above[1L]
      low <- high - 1L
      x0 <- ordered$interaction_log2fc[low]
      x1 <- ordered$interaction_log2fc[high]
      y0 <- ordered$power[low]
      y1 <- ordered$power[high]
      value <- if (y1 == y0) x1 else x0 + (0.80 - y0) * (x1 - x0) / (y1 - y0)
      status <- "linearly interpolated"
    }
    .(mde_80_log2fc = value, mde_80_fold_change = ifelse(is.finite(value), 2^value, NA_real_), status = status)
  }, by = .(design, expression_quartile)]
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "discovery-counts", "discovery-metadata", "discovery-decisions",
  "external-counts", "external-metadata", "external-decisions", "frozen-genes",
  "outdir", "figure-prefix", "source-data", "supplement", "iterations"
)
missing <- setdiff(required, names(args))
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))
iterations <- as.integer(args$iterations)
grid <- if ("grid" %in% names(args)) as.numeric(strsplit(args$grid, ",", fixed = TRUE)[[1L]]) else c(0, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 3.5, 4)
if (anyNA(grid) || any(grid < 0) || anyDuplicated(grid)) stop("Invalid effect grid")
threshold <- log2(1.5)
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

discovery_counts <- read_counts(args[["discovery-counts"]])
discovery_metadata <- load_metadata(args[["discovery-metadata"]], args[["discovery-decisions"]], colnames(discovery_counts))
discovery_fit <- prepare_fit(discovery_counts, discovery_metadata, c("Guiwei", "Yurong1"), "Discovery: genome-wide BH")

external_counts <- read_counts(args[["external-counts"]])
external_metadata <- load_metadata(args[["external-metadata"]], args[["external-decisions"]], colnames(external_counts))
external_metadata <- external_metadata[as.character(time_h) == "24"]
external_counts <- external_counts[, external_metadata$sample_id, drop = FALSE]
frozen_genes <- fread(args[["frozen-genes"]])$gene_id
external_fit <- prepare_fit(
  external_counts, external_metadata, c("Guiwei", "Heiye"),
  "External: candidate-family BH", family_genes = frozen_genes
)

fit_summary <- data.table(
  design = c(discovery_fit$label, external_fit$label),
  tested_family_size = c(length(discovery_fit$genes), length(external_fit$genes)),
  nonnull_targets_per_simulation = c(min(262L, length(discovery_fit$genes)), min(2L, length(external_fit$genes))),
  libraries = c(nrow(discovery_fit$col_data), nrow(external_fit$col_data)),
  libraries_per_cell = 3L,
  multiplicity = c("BH across full expressed genome", "BH across measurable frozen candidate family"),
  support_rule = c("q<0.05 and |estimated log2FC|>=log2(1.5)", "q<0.05, effect threshold, correct prespecified direction, and 95% CI excluding zero")
)
write_tsv(fit_summary, file.path(args$outdir, "simulation_design.tsv"))

raw_parts <- list()
counter <- 0L
for (effect_index in seq_along(grid)) {
  effect <- grid[effect_index]
  for (iteration in seq_len(iterations)) {
    counter <- counter + 1L
    raw_parts[[length(raw_parts) + 1L]] <- simulate_once(
      discovery_fit, effect, iteration, min(262L, length(discovery_fit$genes)), threshold,
      seed = 42000000L + effect_index * 10000L + iteration,
      require_direction = FALSE
    )
    raw_parts[[length(raw_parts) + 1L]] <- simulate_once(
      external_fit, effect, iteration, min(2L, length(external_fit$genes)), threshold,
      seed = 43000000L + effect_index * 10000L + iteration,
      require_direction = TRUE
    )
    if (iteration %% 5L == 0L || iteration == iterations) {
      message(sprintf("H3 progress: effect %.2f, iteration %d/%d", effect, iteration, iterations))
    }
    if (iteration %% 10L == 0L) gc(verbose = FALSE)
  }
}
raw <- rbindlist(raw_parts, use.names = TRUE)
summary <- summarize_power(raw)
mde <- minimum_detectable(summary)
write_tsv(raw, file.path(args$outdir, "power_simulation_raw.tsv.gz"))
write_tsv(summary, args[["source-data"]])
write_tsv(mde, args$supplement)

plot_data <- summary[interaction_log2fc > 0]
plot_data[, expression_quartile := factor(expression_quartile, levels = c("Overall", "Q1", "Q2", "Q3", "Q4"))]
palette <- c("Overall" = "#111827", "Q1" = "#9CA3AF", "Q2" = "#56B4E9", "Q3" = "#009E73", "Q4" = "#D55E00")
p <- ggplot(plot_data, aes(interaction_log2fc, power, color = expression_quartile, group = expression_quartile)) +
  geom_hline(yintercept = 0.80, color = "#6B7280", linetype = "dashed", linewidth = 0.45) +
  geom_vline(xintercept = threshold, color = "#6B7280", linetype = "dotted", linewidth = 0.45) +
  geom_ribbon(aes(ymin = ci_lower, ymax = ci_upper, fill = expression_quartile), alpha = 0.10, color = NA) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 1.8) +
  facet_wrap(~ design, ncol = 2) +
  scale_color_manual(values = palette, drop = FALSE) +
  scale_fill_manual(values = palette, drop = FALSE) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2)) +
  labs(
    x = "True absolute interaction effect (log2 fold change)",
    y = "Detection probability",
    color = "Mean-expression stratum",
    fill = "Mean-expression stratum",
    caption = "Dashed line: 80% power. Dotted line: registered |log2FC| threshold. Parametric power is conditional on fitted means, dispersions, deposited-library independence, and the simulated non-null prevalence."
  ) +
  theme_bw(base_size = 10) +
  theme(legend.position = "bottom", panel.grid.minor = element_blank(), strip.text = element_text(face = "bold"))

prefix <- args[["figure-prefix"]]
dir.create(dirname(prefix), recursive = TRUE, showWarnings = FALSE)
ggsave(paste0(prefix, ".pdf"), p, width = 10.5, height = 5.5)
ggsave(paste0(prefix, ".png"), p, width = 10.5, height = 5.5, dpi = 300)
ggsave(paste0(prefix, ".svg"), p, width = 10.5, height = 5.5, device = grDevices::svg)
ggsave(paste0(prefix, ".tiff"), p, width = 10.5, height = 5.5, dpi = 300, compression = "lzw")

parameters <- list(
  generated_at = format(Sys.time(), tz = "America/New_York", usetz = TRUE),
  iterations_per_effect = iterations,
  effect_grid_log2fc = grid,
  effect_threshold_log2fc = threshold,
  discovery_family_size = length(discovery_fit$genes),
  discovery_nonnull_targets_per_simulation = min(262L, length(discovery_fit$genes)),
  external_family_size = length(external_fit$genes),
  external_nonnull_targets_per_simulation = min(2L, length(external_fit$genes)),
  dispersion_handling = "DESeq2 MAP dispersions fitted once to observed counts and treated as known in parametric Wald simulations",
  null_handling = "fitted main effects retained; interaction coefficient set to zero for background genes",
  sign_handling = "equal-probability positive and negative injected effects",
  limitation = "conditional model-based power, not a correction for unreported biological-unit independence"
)
write_json(parameters, file.path(args$outdir, "power_simulation_parameters.json"), pretty = TRUE, auto_unbox = TRUE)
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "H3_R_sessionInfo.txt"))
message("H3 complete")
