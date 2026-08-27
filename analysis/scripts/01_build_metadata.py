#!/usr/bin/env python3
"""Build locked sample tables and a biological-unit registry from ENA manifests."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


STUDIES = {
    "PRJNA830488": {
        "geo": "GSE201243",
        "modality": "mRNA",
        "role": "discovery",
        "independence": "unresolved_conditional",
        "evidence": "GEO family SOFT plus ENA run manifest; source trees/pooling not reported",
        "expected_runs": 12,
    },
    "PRJNA450886": {
        "geo": "",
        "modality": "mRNA",
        "role": "primary_cross_context",
        "independence": "biological_replicate_label_source_unit_unresolved",
        "evidence": "ENA BioSample aliases/attributes and Sun et al. 2019 (PMCID PMC6391439)",
        "expected_runs": 36,
    },
    "PRJNA922966": {
        "geo": "GSE222651",
        "modality": "mRNA",
        "role": "generic_infection_transfer",
        "independence": "three_biological_replicates_reported",
        "evidence": "GEO family SOFT and Yin et al. 2023 doi:10.3390/agronomy13071904",
        "expected_runs": 12,
    },
    "PRJNA922965": {
        "geo": "GSE222650",
        "modality": "small_RNA",
        "role": "orthogonal_same_cohort",
        "independence": "three_biological_replicates_reported_pairing_not_explicit",
        "evidence": "GEO family SOFT and Yin et al. 2023 doi:10.3390/agronomy13071904",
        "expected_runs": 12,
    },
    "PRJNA1090613": {
        "geo": "GSE262200",
        "modality": "mRNA",
        "role": "exploratory",
        "independence": "unresolved",
        "evidence": "GEO family SOFT plus ENA run manifest; time/phenotype/source units not reported",
        "expected_runs": 12,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", default="analysis/metadata")
    parser.add_argument("--registry", default="analysis/metadata/biological_unit_registry.tsv")
    parser.add_argument("--audit", default="results/audit/metadata_validation.tsv")
    return parser.parse_args()


def parse_design(study: str, record: dict[str, str]) -> dict[str, str]:
    title = record.get("sample_title", "")
    alias = record.get("sample_alias", "")
    if study == "PRJNA830488":
        match = re.fullmatch(r"(GW|YR)_(M|P)(\d+)", title)
        if not match:
            raise ValueError(f"Unrecognized discovery title: {title}")
        cultivar = {"GW": "Guiwei", "YR": "Yurong1"}[match.group(1)]
        treatment = {"M": "mock", "P": "infected"}[match.group(2)]
        return {"cultivar": cultivar, "treatment": treatment, "time_h": "24", "tissue": "leaf", "replicate": match.group(3)}
    if study == "PRJNA450886":
        match = re.fullmatch(r"([GH])([CI])_(6|24|48)hpi_(\d+)", alias)
        if not match:
            raise ValueError(f"Unrecognized PRJNA450886 alias: {alias}")
        return {
            "cultivar": {"G": "Guiwei", "H": "Heiye"}[match.group(1)],
            "treatment": {"C": "mock", "I": "infected"}[match.group(2)],
            "time_h": match.group(3),
            "tissue": "pericarp",
            "replicate": match.group(4),
        }
    if study in {"PRJNA922966", "PRJNA922965"}:
        match = re.search(r"FZX_(Le|Fr)_([MC])(\d+)$", title)
        if not match:
            raise ValueError(f"Unrecognized Feizixiao title: {title}")
        return {
            "cultivar": "Feizixiao",
            "treatment": {"M": "mock", "C": "infected"}[match.group(2)],
            "time_h": "24",
            "tissue": {"Le": "leaf", "Fr": "fruit"}[match.group(1)],
            "replicate": match.group(3),
        }
    if study == "PRJNA1090613":
        match = re.fullmatch(r"leaves, (GW|SFZ)_(Mock|P)(\d+)", title)
        if not match:
            raise ValueError(f"Unrecognized GSE262200 title: {title}")
        return {
            "cultivar": {"GW": "Guiwei", "SFZ": "SFZ_unresolved"}[match.group(1)],
            "treatment": {"Mock": "mock", "P": "infected"}[match.group(2)],
            "time_h": "unreported",
            "tissue": "leaf",
            "replicate": match.group(3),
        }
    raise ValueError(f"Unknown study {study}")


def main() -> int:
    args = parse_args()
    metadata_dir = Path(args.metadata_dir)
    registry_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    for study, settings in STUDIES.items():
        manifest = metadata_dir / f"{study}.tsv"
        with manifest.open(newline="") as handle:
            records = list(csv.DictReader(handle, delimiter="\t"))
        parsed: list[dict[str, str]] = []
        for record in records:
            design = parse_design(study, record)
            sample_id = record["sample_title"].replace("leaves, ", "").replace(" ", "_")
            if study == "PRJNA450886":
                sample_id = record["sample_alias"]
            entry = {
                "sample_id": sample_id,
                "study": study,
                "geo_series": settings["geo"],
                "biosample": record["sample_accession"],
                "experiment": record["experiment_accession"],
                "run": record["run_accession"],
                "cultivar": design["cultivar"],
                "treatment": design["treatment"],
                "time_h": design["time_h"],
                "tissue": design["tissue"],
                "replicate": design["replicate"],
                "modality": settings["modality"],
                "library_layout": record["library_layout"],
                "instrument": record["instrument_model"],
                "read_count": record["read_count"],
                "base_count": record["base_count"],
                "fastq_ftp": record["fastq_ftp"],
                "fastq_md5": record["fastq_md5"],
            }
            parsed.append(entry)
            registry_rows.append(
                {
                    "study": study,
                    "geo_series": settings["geo"],
                    "biosample": record["sample_accession"],
                    "experiment": record["experiment_accession"],
                    "run": record["run_accession"],
                    "cultivar_genotype": design["cultivar"],
                    "tree_orchard_source": "unreported" if study != "PRJNA450886" else "Zhanjiang orchard; exact fruit/tree mapping unreported",
                    "harvest": "unreported",
                    "pooled_material": "unreported",
                    "extraction": "one deposited library; independence details unreported",
                    "library": record["experiment_accession"],
                    "technical_replicate_relationship": "none reported",
                    "treatment": design["treatment"],
                    "tissue": design["tissue"],
                    "time_h": design["time_h"],
                    "batch": record["instrument_model"],
                    "independence_status": settings["independence"],
                    "eligibility_role": settings["role"],
                    "evidence_source": settings["evidence"],
                }
            )
        parsed.sort(key=lambda item: (item["cultivar"], item["tissue"], item["time_h"], item["treatment"], int(item["replicate"])))
        output = metadata_dir / f"{study}_samples.tsv"
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(parsed[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(parsed)
        run_ok = len(parsed) == int(settings["expected_runs"]) and len({item["run"] for item in parsed}) == len(parsed)
        cell_counts = Counter((item["cultivar"], item["treatment"], item["time_h"], item["tissue"]) for item in parsed)
        cells_ok = all(count == 3 for count in cell_counts.values())
        audit_rows.extend(
            [
                {"study": study, "check": "run_count_and_uniqueness", "status": "PASS" if run_ok else "FAIL", "detail": f"observed={len(parsed)} expected={settings['expected_runs']} unique={len({item['run'] for item in parsed})}"},
                {"study": study, "check": "three_libraries_per_design_cell", "status": "PASS" if cells_ok else "FAIL", "detail": ";".join(f"{'|'.join(key)}={value}" for key, value in sorted(cell_counts.items()))},
            ]
        )
    registry = Path(args.registry)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry_rows.sort(key=lambda item: (item["study"], item["cultivar_genotype"], item["tissue"], item["time_h"], item["treatment"], item["run"]))
    with registry.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(registry_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(registry_rows)
    audit = Path(args.audit)
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["study", "check", "status", "detail"], delimiter="\t")
        writer.writeheader()
        writer.writerows(audit_rows)
    failures = [item for item in audit_rows if item["status"] == "FAIL"]
    print(f"Wrote {len(registry_rows)} registry rows and {len(audit_rows)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

