validate_design <- function(metadata, formula) {
  required <- all.vars(formula)
  missing <- setdiff(required, colnames(metadata))
  if (length(missing) > 0L) {
    stop("Metadata missing model fields: ", paste(missing, collapse = ", "))
  }
  matrix <- model.matrix(formula, data = metadata)
  rank <- qr(matrix)$rank
  if (rank != ncol(matrix)) {
    stop(sprintf("Design is rank deficient: rank=%d columns=%d", rank, ncol(matrix)))
  }
  invisible(matrix)
}

