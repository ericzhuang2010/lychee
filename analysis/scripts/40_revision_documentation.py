#!/usr/bin/env python3
"""Write revision supplements for dataset eligibility and exact tool versions."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


SEARCH_DATE = "2026-08-27"


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    supplement = root / "results" / "supplement"

    # These are retrospective, reproducible NCBI E-utilities searches performed
    # during revision. They reconstruct coverage; they are not represented as the
    # unrecorded historical search that preceded the 2026-08-18 protocol freeze.
    queries = [
        {
            "search_date": SEARCH_DATE,
            "database": "NCBI GEO DataSets",
            "record_unit": "GSE series",
            "query": 'gse[ETYP] AND "Litchi chinensis"[Organism] AND (infect*[All Fields] OR inoculat*[All Fields] OR disease[All Fields] OR pathogen*[All Fields] OR "downy blight"[All Fields])',
            "hit_count": 6,
            "returned_accessions": "GSE262200;GSE222652;GSE222651;GSE222650;GSE201243;GSE63658",
            "interpretation": "Broad sensitivity search; GSE222652 is a super-series and GSE63658 is an off-target senescence record.",
            "provenance_status": "retrospective reconstruction",
        },
        {
            "search_date": SEARCH_DATE,
            "database": "NCBI BioProject",
            "record_unit": "BioProject",
            "query": '"Litchi chinensis"[Organism] AND (infect*[All Fields] OR inoculat*[All Fields] OR disease[All Fields] OR pathogen*[All Fields] OR "downy blight"[All Fields])',
            "hit_count": 7,
            "returned_accessions": "PRJNA1157370;PRJNA1090613;PRJNA922966;PRJNA922965;PRJNA830488;PRJNA450886;PRJNA268587",
            "interpretation": "Project-level screening source; five eligible projects and two exclusions.",
            "provenance_status": "retrospective reconstruction",
        },
        {
            "search_date": SEARCH_DATE,
            "database": "NCBI SRA",
            "record_unit": "SRA experiment",
            "query": '"Litchi chinensis"[Organism] AND (Peronophythora[All Fields] OR "downy blight"[All Fields]) AND (RNA-Seq[Strategy] OR miRNA-Seq[Strategy])',
            "hit_count": 42,
            "returned_accessions": "experiment-level records; deduplicated and screened at BioProject/GSE level",
            "interpretation": "Narrow assay-level cross-check; the count is experiments, not independent cohorts.",
            "provenance_status": "retrospective reconstruction",
        },
    ]
    write_tsv(
        supplement / "S16a_dataset_search_queries.tsv",
        queries,
        ["search_date", "database", "record_unit", "query", "hit_count", "returned_accessions", "interpretation", "provenance_status"],
    )

    eligibility = [
        {
            "bioproject": "PRJNA830488", "geo": "GSE201243", "decision": "include",
            "analysis_role": "discovery",
            "reason": "Guiwei and Yurong1 leaves; mock and P. litchii; 24 h; three deposited libraries per cell.",
            "independent_cohort": "yes", "limitations": "Source trees, pooling, harvest units, and extraction independence are unreported.",
        },
        {
            "bioproject": "PRJNA450886", "geo": "not linked as a GSE", "decision": "include",
            "analysis_role": "primary cross-context evaluation",
            "reason": "Guiwei and Heiye fruit pericarp; mock and P. litchii; 6, 24, and 48 h; cultivar interaction estimable.",
            "independent_cohort": "yes", "limitations": "Different tissue and resistant comparator; pooling/source-unit independence unreported.",
        },
        {
            "bioproject": "PRJNA922966", "geo": "GSE222651", "decision": "include",
            "analysis_role": "generic infection/tissue transfer",
            "reason": "Feizixiao leaf and fruit mRNA; mock and P. litchii; 24 h.",
            "independent_cohort": "yes", "limitations": "One cultivar; cannot test a cultivar-by-infection interaction.",
        },
        {
            "bioproject": "PRJNA922965", "geo": "GSE222650", "decision": "include",
            "analysis_role": "orthogonal small-RNA modality",
            "reason": "Paired small-RNA arm of the GSE222651 biological cohort.",
            "independent_cohort": "no", "limitations": "Same biological cohort as PRJNA922966; not an independent replication.",
        },
        {
            "bioproject": "PRJNA1090613", "geo": "GSE262200", "decision": "include with quarantine",
            "analysis_role": "exploratory only",
            "reason": "Guiwei and SFZ leaves; mock and P. litchii; cultivar interaction computationally estimable.",
            "independent_cohort": "yes", "limitations": "Sampling time, SFZ phenotype/identity, and source-unit independence unresolved.",
        },
        {
            "bioproject": "PRJNA1157370", "geo": "not identified", "decision": "exclude",
            "analysis_role": "none",
            "reason": "Different pathogen: Colletotrichum gloeosporioides rather than P. litchii.",
            "independent_cohort": "yes", "limitations": "Outside the pathogen-specific eligibility question.",
        },
        {
            "bioproject": "PRJNA268587", "geo": "GSE63658", "decision": "exclude",
            "analysis_role": "none",
            "reason": "Fruit senescence/storage small-RNA and degradome study; no P. litchii inoculation comparison.",
            "independent_cohort": "yes", "limitations": "Retrieved only because its text mentions pathogen-infection defense.",
        },
        {
            "bioproject": "PRJNA922965;PRJNA922966", "geo": "GSE222652", "decision": "collapse",
            "analysis_role": "super-series container",
            "reason": "Super-series combining GSE222650 and GSE222651; not an additional cohort.",
            "independent_cohort": "no", "limitations": "Avoid double-counting the mRNA and small-RNA records as a third study.",
        },
    ]
    write_tsv(
        supplement / "S16b_dataset_eligibility.tsv",
        eligibility,
        ["bioproject", "geo", "decision", "analysis_role", "reason", "independent_cohort", "limitations"],
    )

    versions = [
        ("STAR", "2.7.10b", "executable --version; resolved environment", "verified installed"),
        ("Salmon", "2.5.1", "executable --version; resolved environment", "verified installed"),
        ("fastp", "1.3.6", "executable --version; resolved environment", "verified installed"),
        ("FastQC", "0.12.1", "analysis/envs/lychee-discovery-resolved.yml", "verified resolved environment"),
        ("MultiQC", "1.35", "analysis/envs/lychee-discovery-resolved.yml", "verified resolved environment"),
        ("featureCounts (Subread)", "2.1.1", "executable -v; resolved environment", "verified installed"),
        ("DESeq2", "1.42.0", "results/discovery/primary/R_sessionInfo.txt", "verified executed"),
        ("edgeR", "4.0.16", "results/discovery/dtu/dtu_sessionInfo.txt; resolved environment", "verified executed"),
        ("DRIMSeq", "1.30.0", "results/discovery/dtu/dtu_sessionInfo.txt", "verified executed"),
        ("DEXSeq", "1.48.0", "results/discovery/dtu/dtu_sessionInfo.txt", "verified executed"),
        ("stageR", "1.24.0", "results/discovery/dtu/dtu_sessionInfo.txt", "verified executed"),
        ("apeglm", "1.24.0", "results/discovery/primary/R_sessionInfo.txt", "verified executed"),
        ("MEME Suite (AME/FIMO)", "5.5.9", "executable -version; resolved environment", "verified installed"),
        ("DIAMOND", "2.2.5", "executable version; resolved environment", "verified installed"),
        ("GenMap", "1.3.0", "analysis/envs/lychee-discovery.yml", "pinned specification; executable absent from reconstructed environment"),
        ("Snakemake", "9.25.2", "executable --version; resolved environment", "verified installed"),
        ("R", "4.3.3", "R --version; R sessionInfo files", "verified executed"),
        ("Bioconductor", "3.18", "R 4.3 package series and BiocManager version", "verified environment"),
        ("BiocParallel", "1.36.0", "results/discovery/primary/R_sessionInfo.txt", "verified executed"),
    ]
    version_rows = [
        {"software": software, "version": version, "evidence": evidence, "status": status}
        for software, version, evidence, status in versions
    ]
    write_tsv(
        supplement / "S17_exact_tool_versions.tsv",
        version_rows,
        ["software", "version", "evidence", "status"],
    )

    print(f"wrote {len(queries)} searches, {len(eligibility)} eligibility rows, and {len(version_rows)} version rows")


if __name__ == "__main__":
    main()
