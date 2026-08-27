# Source-installed environment packages

IHW_1.30.0.tar.gz is the official Bioconductor 3.18 source archive. Bioconda
does not publish the corresponding IHW build for R 4.3, so it is installed
after the conda transaction by install_bioconductor_source_packages.R.

The conda environment pins the load-tested lpsymphony 1.28.1 binary. An
official lpsymphony 1.30.0 source build was evaluated but rejected because its
bundled Cgl library failed the package load test with an unresolved symbol.
The unused source archive is retained only as an audit artifact and is not part
of the required installation or checksum manifest.
