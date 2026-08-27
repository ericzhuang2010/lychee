#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(DRIMSeq)
  library(stageR)
  library(DEXSeq)
  library(BiocParallel)
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

empty_dtu <- function() {
  data.table(
    gene_id = character(), transcript_id = character(),
    stage_gene_q = numeric(), stage_transcript_q = numeric(),
    usage_interaction_difference = numeric(), expected_direction = character(),
    exact_sequence_duplicate_status = character(), transcript_mappability_status = character(),
    dtu_status = character(), reason = character()
  )
}

read_meta_metric <- function(path) {
  value <- fromJSON(path, simplifyVector = TRUE)
  percent <- value$percent_mapped
  if (is.null(percent) && !is.null(value$num_mapped) && !is.null(value$num_processed)) {
    percent <- value$num_mapped / value$num_processed
  }
  if (is.null(percent)) percent <- NA_real_
  percent <- as.numeric(percent)
  if (!is.na(percent) && percent > 1) percent <- percent / 100
  bootstraps <- value$num_bootstraps
  if (is.null(bootstraps)) bootstraps <- value$numBootstraps
  if (is.null(bootstraps)) bootstraps <- NA_integer_
  list(mapping_rate = percent, bootstraps = as.integer(bootstraps))
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c(
  "metadata", "decisions", "salmon-root", "tx2gene", "duplicate-clusters",
  "config", "operational-config", "outdir"
)
missing <- required[!required %in% names(args)]
if (length(missing)) stop("Missing arguments: ", paste(missing, collapse = ", "))
config <- fromJSON(args$config, simplifyVector = TRUE)
operational <- fromJSON(args[["operational-config"]], simplifyVector = TRUE)
settings <- operational$dtu
set.seed(as.integer(config$random_seed))
dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)

metadata <- merge(
  fread(args$metadata), fread(args$decisions),
  by = "sample_id", all.x = TRUE, sort = FALSE
)[primary_status == "INCLUDE"]
metadata[, cultivar := factor(cultivar, levels = c("Guiwei", "Yurong1"))]
metadata[, treatment := factor(treatment, levels = c("mock", "infected"))]
design_full <- model.matrix(~ cultivar + treatment + cultivar:treatment, metadata)
if (qr(design_full)$rank != ncol(design_full)) stop("DTU design is not full rank")
interaction_coefficient <- "cultivarYurong1:treatmentinfected"
if (!interaction_coefficient %in% colnames(design_full)) {
  stop("Locked DTU interaction coefficient is unavailable")
}

salmon_files <- file.path(args[["salmon-root"]], metadata$sample_id, "quant.sf")
names(salmon_files) <- metadata$sample_id
meta_files <- file.path(args[["salmon-root"]], metadata$sample_id, "aux_info", "meta_info.json")
if (any(!file.exists(c(salmon_files, meta_files)))) stop("Missing Salmon DTU inputs")
qc_metrics <- rbindlist(lapply(seq_along(meta_files), function(index) {
  observed <- read_meta_metric(meta_files[index])
  data.table(
    sample_id = metadata$sample_id[index],
    salmon_mapping_rate = observed$mapping_rate,
    bootstrap_replicates = observed$bootstraps
  )
}))
qc_metrics[, mapping_gate := !is.na(salmon_mapping_rate) &
             salmon_mapping_rate >= as.numeric(config$dtu_gate$minimum_salmon_mapping_rate)]
qc_metrics[, bootstrap_gate := !is.na(bootstrap_replicates) &
             bootstrap_replicates >= as.integer(settings$require_bootstrap_replicates)]

tx2gene <- fread(args$tx2gene)
setnames(tx2gene, names(tx2gene)[1:2], c("transcript_id", "gene_id"))
duplicates <- fread(args[["duplicate-clusters"]])
duplicate_ids <- unique(c(duplicates[[1L]], duplicates[[2L]]))
quant_long <- rbindlist(lapply(seq_along(salmon_files), function(index) {
  quant <- fread(salmon_files[index])
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
if (anyNA(quant_long$gene_id)) stop("Mapped Salmon transcript lacks a gene mapping")
quant_long[, exact_sequence_duplicate := transcript_id %in% duplicate_ids]
quant_eligible <- quant_long[exact_sequence_duplicate == FALSE]

count_wide <- dcast(
  quant_eligible,
  gene_id + transcript_id ~ sample_id,
  value.var = "count", fill = 0
)
sample_columns <- metadata$sample_id
setnames(count_wide, "transcript_id", "feature_id")
setcolorder(count_wide, c("gene_id", "feature_id", sample_columns))
for (column in sample_columns) set(count_wide, j = column, value = round(count_wide[[column]]))
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
retained_gene_counts <- filtered_counts[, .N, by = gene_id]
retained_multi_isoform_genes <- retained_gene_counts[
  N >= as.integer(settings$minimum_retained_transcripts_per_gene), .N
]

gate <- rbindlist(list(
  qc_metrics[, .(
    gate = paste0("mapping_rate_", sample_id),
    observed = salmon_mapping_rate,
    threshold = as.numeric(config$dtu_gate$minimum_salmon_mapping_rate),
    status = fifelse(mapping_gate, "PASS", "FAIL")
  )],
  qc_metrics[, .(
    gate = paste0("bootstrap_count_", sample_id),
    observed = bootstrap_replicates,
    threshold = as.integer(settings$require_bootstrap_replicates),
    status = fifelse(bootstrap_gate, "PASS", "FAIL")
  )],
  data.table(
    gate = "genes_with_at_least_two_retained_isoforms",
    observed = retained_multi_isoform_genes,
    threshold = as.integer(config$dtu_gate$minimum_genes_with_multiple_isoforms),
    status = fifelse(
      retained_multi_isoform_genes >=
        as.integer(config$dtu_gate$minimum_genes_with_multiple_isoforms),
      "PASS", "FAIL"
    )
  ),
  data.table(
    gate = "exact_duplicate_transcripts_excluded",
    observed = length(duplicate_ids), threshold = 0,
    status = "PASS"
  )
), use.names = TRUE)
write_tsv(qc_metrics, file.path(args$outdir, "salmon_dtu_qc.tsv"))
write_tsv(gate, file.path(args$outdir, "dtu_gate.tsv"))
write_tsv(data.table(
  transcript_id = duplicate_ids,
  exact_sequence_duplicate_status = "EXCLUDED_FROM_DTU"
), file.path(args$outdir, "exact_sequence_duplicate_transcripts.tsv"))

if (any(gate$status == "FAIL")) {
  write_tsv(empty_dtu(), file.path(args$outdir, "frozen_dtu_input.tsv"))
  write_tsv(empty_dtu(), file.path(args$outdir, "all_dtu_results.tsv"))
  writeLines(c(
    "# Conditional DTU result", "",
    "- The preregistered DTU gate failed; no inferential DTU model was run.",
    paste0("- Failed gates: ", paste(gate[status == "FAIL", gate], collapse = ", ")),
    "- The frozen DTU result is empty rather than replaced by a post hoc analysis."
  ), file.path(args$outdir, "dtu_summary.md"))
  quit(save = "no", status = 0L)
}

# Primary DRIMSeq interaction test.
set.seed(as.integer(config$random_seed))
d <- dmPrecision(d, design = design_full, BPPARAM = SerialParam())
d <- dmFit(
  d, design = design_full, one_way = FALSE, bb_model = TRUE,
  BPPARAM = SerialParam(), verbose = 1
)
d <- dmTest(
  d, coef = interaction_coefficient,
  BPPARAM = SerialParam(), verbose = 1
)
gene_result <- as.data.table(DRIMSeq::results(d))
feature_result <- as.data.table(DRIMSeq::results(d, level = "feature"))
write_tsv(gene_result, file.path(args$outdir, "drimseq_gene_results.tsv"))
write_tsv(feature_result, file.path(args$outdir, "drimseq_transcript_results.tsv"))

# DRIMSeq can return undefined p-values for non-estimable genes/transcripts.
# stageR's documented allowNA path removes genes with undefined screening tests
# and leaves undefined confirmation tests uncallable. Audit their counts before
# the adjustment so this behavior is explicit in the frozen result bundle.
stage_na_audit <- data.table(
  metric = c("gene_screening_pvalue_na", "transcript_confirmation_pvalue_na"),
  observed = c(sum(is.na(gene_result$pvalue)), sum(is.na(feature_result$pvalue))),
  handling = c(
    "excluded_from_stageR_screening_and_confirmation",
    "retained_as_na_and_not_discovered"
  )
)
write_tsv(stage_na_audit, file.path(args$outdir, "stageR_na_pvalue_audit.tsv"))

p_screen <- gene_result$pvalue
names(p_screen) <- gene_result$gene_id
p_confirmation <- matrix(feature_result$pvalue, ncol = 1)
rownames(p_confirmation) <- feature_result$feature_id
tx_gene_stage <- as.data.frame(feature_result[, .(feature_id, gene_id)])
stage_object <- stageRTx(
  pScreen = p_screen,
  pConfirmation = p_confirmation,
  pScreenAdjusted = FALSE,
  tx2gene = tx_gene_stage
)
stage_object <- stageWiseAdjustment(
  object = stage_object,
  method = settings$stageR_method,
  alpha = as.numeric(config$dtu_gate$ofdr_max),
  allowNA = TRUE
)
adjusted <- as.data.table(getAdjustedPValues(
  stage_object, order = FALSE, onlySignificantGenes = FALSE
))
setnames(
  adjusted,
  c("geneID", "txID", "gene", "transcript"),
  c("gene_id", "transcript_id", "stage_gene_q", "stage_transcript_q")
)

# Expected transfer direction is the interaction in observed mean usage.
filtered_long <- melt(
  filtered_counts,
  id.vars = c("gene_id", "feature_id"),
  variable.name = "sample_id", value.name = "count"
)
filtered_long <- merge(
  filtered_long,
  metadata[, .(sample_id, cultivar, treatment)],
  by = "sample_id", all.x = TRUE, sort = FALSE
)
filtered_long[, gene_total := sum(count), by = .(gene_id, sample_id)]
filtered_long[, proportion := fifelse(gene_total > 0, count / gene_total, 0)]
filtered_long[, cell := paste(as.character(cultivar), as.character(treatment), sep = "_")]
cell_means <- filtered_long[, .(
  mean_proportion = mean(proportion)
), by = .(gene_id, feature_id, cell)]
usage <- dcast(
  cell_means, gene_id + feature_id ~ cell,
  value.var = "mean_proportion", fill = 0
)
needed_cells <- c("Guiwei_mock", "Guiwei_infected", "Yurong1_mock", "Yurong1_infected")
if (!all(needed_cells %in% names(usage))) stop("DTU usage cells are incomplete")
usage[, usage_interaction_difference :=
        (Yurong1_infected - Yurong1_mock) - (Guiwei_infected - Guiwei_mock)]
setnames(usage, "feature_id", "transcript_id")

all_result <- merge(adjusted, usage, by = c("gene_id", "transcript_id"), all.x = TRUE)
all_result <- merge(
  all_result,
  feature_result[, .(
    gene_id, transcript_id = feature_id,
    drimseq_lr = lr, drimseq_df = df, drimseq_p = pvalue, drimseq_q = adj_pvalue
  )],
  by = c("gene_id", "transcript_id"), all.x = TRUE
)
all_result[, expected_direction := fifelse(
  usage_interaction_difference > 0,
  "positive_usage_interaction",
  fifelse(usage_interaction_difference < 0, "negative_usage_interaction", "zero")
)]
all_result[, exact_sequence_duplicate_status := "PASS_NOT_IN_DUPLICATE_CLUSTER"]
all_result[, transcript_mappability_status := "PASS_EXACT_DUPLICATES_EXCLUDED"]
all_result[, dtu_status := fifelse(
  !is.na(stage_gene_q) & stage_gene_q < as.numeric(config$dtu_gate$ofdr_max) &
    !is.na(stage_transcript_q) & stage_transcript_q < as.numeric(config$dtu_gate$ofdr_max),
  "DISCOVERED", "NOT_DISCOVERED"
)]
all_result[, reason := fifelse(
  dtu_status == "DISCOVERED", "stageR_OFDR_pass", "stageR_OFDR_not_passed"
)]
setorder(all_result, stage_gene_q, stage_transcript_q, gene_id, transcript_id, na.last = TRUE)
write_tsv(all_result, file.path(args$outdir, "all_dtu_results.tsv"))
write_tsv(
  all_result[dtu_status == "DISCOVERED"],
  file.path(args$outdir, "frozen_dtu_input.tsv")
)

# DEXSeq is a sensitivity analysis and does not alter the primary frozen call.
dex_count <- as.matrix(filtered_counts[, setdiff(names(filtered_counts), c("gene_id", "feature_id")), with = FALSE])
rownames(dex_count) <- filtered_counts$feature_id
storage.mode(dex_count) <- "integer"
dex_sample <- as.data.frame(metadata)
rownames(dex_sample) <- dex_sample$sample_id
dex_sample <- dex_sample[colnames(dex_count), , drop = FALSE]
dex_design <- ~ sample + exon + cultivar:exon + treatment:exon + cultivar:treatment:exon
dex_reduced <- ~ sample + exon + cultivar:exon + treatment:exon
dxd <- DEXSeqDataSet(
  countData = dex_count,
  sampleData = dex_sample,
  design = dex_design,
  featureID = filtered_counts$feature_id,
  groupID = filtered_counts$gene_id
)
dxd <- estimateSizeFactors(dxd)
dxd <- estimateDispersions(dxd, BPPARAM = SerialParam())
dxd <- testForDEU(
  dxd, fullModel = dex_design, reducedModel = dex_reduced,
  BPPARAM = SerialParam()
)
dxr <- DEXSeqResults(dxd, independentFiltering = FALSE)
dex_result <- as.data.table(as.data.frame(dxr), keep.rownames = "row_id")
dex_gene_q <- perGeneQValue(dxr)
dex_result[, dexseq_gene_q := unname(dex_gene_q[as.character(groupID)])]
dex_atomic_columns <- names(dex_result)[vapply(
  dex_result, function(column) is.atomic(column) && !is.list(column), logical(1)
)]
dex_result <- dex_result[, dex_atomic_columns, with = FALSE]
write_tsv(dex_result, file.path(args$outdir, "dexseq_sensitivity.tsv"))

writeLines(c(
  "# Conditional DTU result", "",
  sprintf("- Genes with at least two expressed nonduplicate transcripts: %d",
          retained_multi_isoform_genes),
  sprintf("- DRIMSeq/stageR discovered transcript rows at OFDR < %.3g: %d",
          as.numeric(config$dtu_gate$ofdr_max), sum(all_result$dtu_status == "DISCOVERED")),
  sprintf("- Undefined DRIMSeq screening/confirmation p-values: %d genes / %d transcripts; stageR allowNA handling made them ineligible for discovery.",
          stage_na_audit[metric == "gene_screening_pvalue_na", observed],
          stage_na_audit[metric == "transcript_confirmation_pvalue_na", observed]),
  "- Exact sequence-duplicate clusters were excluded uniformly before modeling.",
  "- DEXSeq is reported as sensitivity and cannot create a primary DTU call.",
  "- External outcomes remained closed."
), file.path(args$outdir, "dtu_summary.md"))
writeLines(capture.output(sessionInfo()), file.path(args$outdir, "dtu_sessionInfo.txt"))
