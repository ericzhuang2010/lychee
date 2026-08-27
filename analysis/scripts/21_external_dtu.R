#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DRIMSeq)
  library(BiocParallel)
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

empty_result <- function() {
  data.table(
    study = character(), gene_id = character(), transcript_id = character(),
    discovery_usage_interaction_difference = numeric(), expected_direction = character(),
    external_usage_difference = numeric(), external_direction = character(),
    external_dtu_p = numeric(), external_dtu_q = numeric(), measurable = logical(),
    direction_agrees = logical(), external_dtu_status = character(),
    can_promote_tier_a = logical(), reason = character()
  )
}

empty_nontranscript_targets <- function() {
  data.table(
    transcript_id = character(), sample_id = character(), count = numeric(),
    exclusion_reason = character()
  )
}

read_mapping_rate <- function(path) {
  value <- fromJSON(path, simplifyVector = TRUE)
  rate <- value$percent_mapped
  if (is.null(rate) && !is.null(value$num_mapped) && !is.null(value$num_processed)) {
    rate <- value$num_mapped / value$num_processed
  }
  rate <- as.numeric(rate)
  if (length(rate) != 1L || is.na(rate)) return(NA_real_)
  if (rate > 1) rate <- rate / 100
  rate
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "frozen-dtu", "metadata", "decisions", "salmon-root", "tx2gene",
  "discovery-config", "operational-config", "external-config", "study", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))

study <- args$study
discovery_config <- fromJSON(args[["discovery-config"]], simplifyVector = TRUE)
operational <- fromJSON(args[["operational-config"]], simplifyVector = TRUE)
external_config <- fromJSON(args[["external-config"]], simplifyVector = TRUE)
settings <- operational$dtu
set.seed(as.integer(discovery_config$random_seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

frozen <- fread(args[["frozen-dtu"]])
if (!nrow(frozen)) {
  write_tsv(empty_result(), file.path(args$outdir, "frozen_dtu_external_tests.tsv"))
  write_tsv(
    empty_nontranscript_targets(),
    file.path(args$outdir, "salmon_nontranscript_targets.tsv")
  )
  write_tsv(data.table(
    metric = "frozen_dtu_events", observed = 0, threshold = 1, status = "NOT_APPLICABLE"
  ), file.path(args$outdir, "external_dtu_gate.tsv"))
  writeLines(c(
    paste0("# External DTU assessment: ", study), "",
    "- The frozen discovery DTU set is empty; no external event was substituted."
  ), file.path(args$outdir, "external_dtu_summary.md"))
  quit(save = "no", status = 0L)
}
if (anyDuplicated(frozen[, .(gene_id, transcript_id)])) stop("Duplicate frozen DTU event")

metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)[primary_status == "INCLUDE"]
if (study == "PRJNA922966") metadata <- metadata[tissue == "leaf"]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
if (study == "PRJNA450886") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Heiye"))]
  metadata[, time := factor(as.character(time_h), levels = c("24", "6", "48"))]
  design <- model.matrix(~ cultivar * treatment * time, metadata)
  coefficient_name <- "cultivarHeiye:treatmentinfected"
} else if (study == "PRJNA922966") {
  design <- model.matrix(~ treatment, metadata)
  coefficient_name <- "treatmentinfected"
} else if (study == "PRJNA1090613") {
  metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "SFZ_unresolved"))]
  design <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
  coefficient_name <- "cultivarSFZ_unresolved:treatmentinfected"
} else {
  stop("Unsupported study: ", study)
}
if (qr(design)$rank != ncol(design) || !coefficient_name %in% colnames(design)) {
  stop("External DTU design/contrast is invalid")
}

quant_files <- file.path(args[["salmon-root"]], metadata$sample_id, "quant.sf")
meta_files <- file.path(args[["salmon-root"]], metadata$sample_id, "aux_info", "meta_info.json")
if (any(!file.exists(c(quant_files, meta_files)))) stop("Missing external Salmon files")
mapping_rates <- vapply(meta_files, read_mapping_rate, numeric(1))
mapping_pass <- all(
  is.finite(mapping_rates) &
    mapping_rates >= as.numeric(discovery_config$dtu_gate$minimum_salmon_mapping_rate)
)

tx2gene <- fread(args$tx2gene)
setnames(tx2gene, names(tx2gene)[1:2], c("transcript_id", "gene_id"))
target_genes <- unique(frozen$gene_id)
quant_long <- rbindlist(lapply(seq_along(quant_files), function(index) {
  quant <- fread(quant_files[index])
  if (!all(c("Name", "NumReads") %in% names(quant))) stop("Malformed Salmon quant.sf")
  quant[, .(
    transcript_id = Name,
    sample_id = metadata$sample_id[index],
    count = as.numeric(NumReads)
  )]
}))
nontranscript_targets <- quant_long[!transcript_id %in% tx2gene$transcript_id]
nontranscript_targets[, exclusion_reason := "gentrome_target_absent_from_frozen_tx2gene"]
write_tsv(
  nontranscript_targets,
  file.path(args$outdir, "salmon_nontranscript_targets.tsv")
)
quant_long <- merge(quant_long, tx2gene, by = "transcript_id", all = FALSE, sort = FALSE)
if (anyNA(quant_long$gene_id)) stop("Mapped external Salmon transcript lacks gene mapping")
quant_long <- quant_long[gene_id %in% target_genes]

target_adequacy <- quant_long[
  frozen[, .(gene_id, transcript_id)],
  on = .(gene_id, transcript_id), nomatch = 0
][, .(
  transcript_count_samples = sum(count >= as.numeric(settings$minimum_transcript_count))
), by = .(gene_id, transcript_id)]
gene_adequacy <- quant_long[, .(
  gene_count_samples = sum(tapply(count, sample_id, sum) >= as.numeric(settings$minimum_gene_count))
), by = gene_id]
target_adequacy <- merge(target_adequacy, gene_adequacy, by = "gene_id", all.x = TRUE)
target_adequacy[, measurable :=
  transcript_count_samples >= as.integer(settings$minimum_transcript_count_samples) &
  gene_count_samples >= as.integer(settings$minimum_gene_count_samples)]

gate <- rbindlist(list(
  data.table(
    metric = "included_salmon_mapping_rate",
    observed = min(mapping_rates, na.rm = TRUE),
    threshold = as.numeric(discovery_config$dtu_gate$minimum_salmon_mapping_rate),
    status = if (mapping_pass) "PASS" else "FAIL"
  ),
  data.table(
    metric = "measurable_frozen_transcript_events",
    observed = sum(target_adequacy$measurable),
    threshold = 1,
    status = if (any(target_adequacy$measurable)) "PASS" else "FAIL"
  )
))
write_tsv(gate, file.path(args$outdir, "external_dtu_gate.tsv"))

if (!mapping_pass || !any(target_adequacy$measurable)) {
  result <- merge(
    frozen[, .(
      gene_id, transcript_id,
      discovery_usage_interaction_difference = usage_interaction_difference,
      expected_direction
    )],
    target_adequacy,
    by = c("gene_id", "transcript_id"), all.x = TRUE, sort = FALSE
  )
  result[, `:=`(
    study = study,
    external_usage_difference = NA_real_, external_direction = NA_character_,
    external_dtu_p = NA_real_, external_dtu_q = NA_real_,
    measurable = FALSE, direction_agrees = NA,
    external_dtu_status = "not_testable", can_promote_tier_a = FALSE,
    reason = if (!mapping_pass) "external_salmon_mapping_gate_failed" else "frozen_transcript_not_measurable"
  )]
  write_tsv(result, file.path(args$outdir, "frozen_dtu_external_tests.tsv"))
  writeLines(c(
    paste0("# External DTU assessment: ", study), "",
    "- The external DTU gate failed; all frozen events are reported as not testable."
  ), file.path(args$outdir, "external_dtu_summary.md"))
  quit(save = "no", status = 0L)
}

count_wide <- dcast(
  quant_long,
  gene_id + transcript_id ~ sample_id,
  value.var = "count", fill = 0
)
setnames(count_wide, "transcript_id", "feature_id")
setcolorder(count_wide, c("gene_id", "feature_id", metadata$sample_id))
for (column in metadata$sample_id) set(count_wide, j = column, value = round(count_wide[[column]]))
sample_table <- as.data.frame(metadata)
rownames(sample_table) <- sample_table$sample_id
d <- dmDSdata(counts = as.data.frame(count_wide), samples = sample_table)
d <- dmFilter(
  d,
  min_samps_gene_expr = as.integer(settings$minimum_gene_count_samples),
  min_samps_feature_expr = as.integer(settings$minimum_transcript_count_samples),
  min_gene_expr = as.numeric(settings$minimum_gene_count),
  min_feature_expr = as.numeric(settings$minimum_transcript_count),
  min_samps_feature_prop = as.integer(settings$minimum_transcript_proportion_samples),
  min_feature_prop = as.numeric(settings$minimum_transcript_proportion)
)
filtered_counts <- as.data.table(counts(d))
retained <- filtered_counts[, .N, by = gene_id][N >= 2L, gene_id]
if (!length(retained)) {
  result <- frozen[, .(
    study = study, gene_id, transcript_id,
    discovery_usage_interaction_difference = usage_interaction_difference,
    expected_direction,
    external_usage_difference = NA_real_, external_direction = NA_character_,
    external_dtu_p = NA_real_, external_dtu_q = NA_real_, measurable = FALSE,
    direction_agrees = NA, external_dtu_status = "not_testable",
    can_promote_tier_a = FALSE, reason = "fewer_than_two_external_transcripts_after_filter"
  )]
  write_tsv(result, file.path(args$outdir, "frozen_dtu_external_tests.tsv"))
  writeLines(c(
    paste0("# External DTU assessment: ", study), "",
    "- No frozen gene retained two external transcripts; all events are not testable."
  ), file.path(args$outdir, "external_dtu_summary.md"))
  quit(save = "no", status = 0L)
}

set.seed(as.integer(discovery_config$random_seed))
d <- dmPrecision(d, design = design, BPPARAM = SerialParam())
d <- dmFit(d, design = design, one_way = FALSE, bb_model = TRUE,
           BPPARAM = SerialParam(), verbose = 0)
d <- dmTest(d, coef = coefficient_name, BPPARAM = SerialParam(), verbose = 0)
feature_result <- as.data.table(DRIMSeq::results(d, level = "feature"))[, .(
  gene_id, transcript_id = feature_id, external_dtu_lr = lr,
  external_dtu_df = df, external_dtu_p = pvalue
)]

long <- melt(
  filtered_counts,
  id.vars = c("gene_id", "feature_id"),
  variable.name = "sample_id", value.name = "count"
)
long <- merge(long, metadata, by = "sample_id", all.x = TRUE, sort = FALSE)
long[, gene_total := sum(count), by = .(gene_id, sample_id)]
long[, proportion := fifelse(gene_total > 0, count / gene_total, 0)]
if (study == "PRJNA450886") {
  long <- long[as.character(time) == "24"]
  long[, cell := paste(as.character(cultivar), as.character(treatment), sep = "_")]
  means <- dcast(long[, .(mean = mean(proportion)), by = .(gene_id, feature_id, cell)],
                 gene_id + feature_id ~ cell, value.var = "mean", fill = 0)
  means[, external_usage_difference :=
          (Heiye_infected - Heiye_mock) - (Guiwei_infected - Guiwei_mock)]
} else if (study == "PRJNA922966") {
  means <- dcast(long[, .(mean = mean(proportion)), by = .(gene_id, feature_id, treatment)],
                 gene_id + feature_id ~ treatment, value.var = "mean", fill = 0)
  means[, external_usage_difference := infected - mock]
} else {
  long[, cell := paste(as.character(cultivar), as.character(treatment), sep = "_")]
  means <- dcast(long[, .(mean = mean(proportion)), by = .(gene_id, feature_id, cell)],
                 gene_id + feature_id ~ cell, value.var = "mean", fill = 0)
  means[, external_usage_difference :=
          (SFZ_unresolved_infected - SFZ_unresolved_mock) - (Guiwei_infected - Guiwei_mock)]
}
setnames(means, "feature_id", "transcript_id")

result <- merge(
  frozen[, .(
    gene_id, transcript_id,
    discovery_usage_interaction_difference = usage_interaction_difference,
    expected_direction
  )],
  feature_result,
  by = c("gene_id", "transcript_id"), all.x = TRUE, sort = FALSE
)
result <- merge(
  result,
  means[, .(gene_id, transcript_id, external_usage_difference)],
  by = c("gene_id", "transcript_id"), all.x = TRUE, sort = FALSE
)
result <- merge(result, target_adequacy, by = c("gene_id", "transcript_id"), all.x = TRUE)
result[, external_dtu_q := {
  value <- rep(NA_real_, .N)
  finite <- is.finite(external_dtu_p)
  value[finite] <- p.adjust(external_dtu_p[finite], method = "BH")
  value
}]
result[, `:=`(
  external_direction = fifelse(
    external_usage_difference > 0, "positive_usage_interaction",
    fifelse(external_usage_difference < 0, "negative_usage_interaction", "zero")
  ),
  measurable = measurable & is.finite(external_usage_difference) & is.finite(external_dtu_p)
)]
result[, direction_agrees := measurable & external_direction == expected_direction]
result[, external_dtu_status := fcase(
  !measurable, "not_testable",
  external_dtu_q < as.numeric(external_config$gene_support$bh_q_max) & direction_agrees,
    "cross_context_supported",
  external_dtu_q < as.numeric(external_config$gene_support$bh_q_max) & !direction_agrees,
    "contradictory",
  default = "unsupported"
)]
result[, `:=`(
  study = study,
  can_promote_tier_a = FALSE,
  reason = fifelse(measurable, "frozen_event_tested", "frozen_event_not_measurable")
)]
setorder(result, external_dtu_q, gene_id, transcript_id, na.last = TRUE)
write_tsv(result, file.path(args$outdir, "frozen_dtu_external_tests.tsv"))
writeLines(c(
  paste0("# External DTU assessment: ", study), "",
  sprintf("- Frozen transcript events: %d", nrow(frozen)),
  sprintf("- Measurable external events: %d", sum(result$measurable)),
  sprintf("- Same-direction cross-context DTU support: %d",
          sum(result$external_dtu_status == "cross_context_supported")),
  sprintf("- Contradictory DTU events: %d", sum(result$external_dtu_status == "contradictory")),
  "- No external DTU result changes frozen discovery membership.",
  "- DTU transfer is labeled cross-context rather than direct replication."
), file.path(args$outdir, "external_dtu_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "external_dtu_sessionInfo.txt"))
