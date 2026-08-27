#!/usr/bin/env Rscript

# Bioconda does not publish an IHW build for the R 4.3 / Bioconductor 3.18
# combination. The compatible lpsymphony 1.28.1 binary is pinned in the conda
# environment; install only the checksummed official IHW source tarball.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
  stop("usage: install_bioconductor_source_packages.R SOURCE_DIRECTORY")
}

source_directory <- normalizePath(args[[1]], mustWork = TRUE)
tarball <- file.path(source_directory, "IHW_1.30.0.tar.gz")
if (!file.exists(tarball)) {
  stop("missing source tarball: ", tarball)
}

if (packageVersion("lpsymphony") != "1.28.1") {
  stop("expected the pinned lpsymphony 1.28.1 binary")
}
status <- system2(
  file.path(R.home("bin"), "R"),
  c("CMD", "INSTALL", shQuote(tarball))
)
if (status != 0L) {
  stop("R CMD INSTALL failed for ", tarball)
}

stopifnot(
  packageVersion("lpsymphony") == "1.28.1",
  packageVersion("IHW") == "1.30.0"
)
cat("Official Bioconductor source package validation PASS\n")
