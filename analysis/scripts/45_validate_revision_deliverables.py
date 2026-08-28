#!/usr/bin/env python3
"""Assert completeness and internal consistency of H1--H10 revision deliverables."""

from __future__ import annotations

import argparse
import csv
import gzip
import subprocess
import tarfile
import zipfile
from pathlib import Path


GIT_FILE_LIMIT = 100_000_000


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, mode="rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def truth(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def row_count(path: Path) -> int:
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, mode="rt", encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f"Missing or empty artifact: {path}")


def current_git_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    )
    return [root / value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--date", default="2026-08-27")
    args = parser.parse_args()
    root = args.root.resolve()

    # H1 and H2
    s14 = rows(root / "results/supplement/S14_legacy_within_cultivar_audit.tsv")
    assert len(s14) == 36
    assert len({row["gene_id"] for row in s14}) == 18
    expected_h1 = {"Guiwei": (13, 13), "Yurong1": (16, 15)}
    for cultivar, (q_count, both_count) in expected_h1.items():
        subset = [row for row in s14 if row["cultivar"] == cultivar]
        assert len(subset) == 18
        assert sum(truth(row["q_lt_0_05"]) for row in subset) == q_count
        assert sum(truth(row["q_and_effect_pass"]) for row in subset) == both_count

    h2 = rows(root / "results/revision/H2_composite_null_summary.tsv")
    assert [(int(row["input_count"]), int(row["composite_null_q_lt_0_05"]), int(row["apeglm_fsos_svalue_lt_0_05"])) for row in h2] == [
        (262, 8, 149), (206, 7, 113), (19, 7, 18), (16, 7, 15)
    ]
    s3 = rows(root / "results/supplement/S3_all_discovery_statistics.tsv")
    assert len(s3) == 19_445 and len({row["gene_id"] for row in s3}) == 19_445
    required_h2_columns = {
        "composite_null_q", "composite_null_pass", "apeglm_fsos_svalue",
        "apeglm_fsos_svalue_lt_0_05",
    }
    assert required_h2_columns <= set(s3[0])

    # H4--H9 tables and figures
    s15 = rows(root / "results/supplement/S15_controlled_motif_background.tsv")
    assert len(s15) == 21
    matched = [row for row in s15 if row["background_strategy"] == "expression_GC_matched_genomic"]
    assert len(matched) == 7 and sum(truth(row["enriched_q_lt_0_05"]) for row in matched) == 4
    assert [row["element"] for row in s15 if truth(row["recount_matches_published"])] == ["ARE", "ARE", "ARE"]

    assert len(rows(root / "results/supplement/S16a_dataset_search_queries.tsv")) == 3
    assert len(rows(root / "results/supplement/S16b_dataset_eligibility.tsv")) == 8
    assert len(rows(root / "results/supplement/S17_exact_tool_versions.tsv")) == 19

    figure_s1 = rows(root / "results/figures/source_data/FigureS1_replicate_level_counts_source_data.tsv")
    assert len(figure_s1) == 192 and len({row["gene_id"] for row in figure_s1}) == 16
    pca = rows(root / "results/figures/source_data/UnifiedFigure1_PCA_source_data.tsv")
    assert len(pca) == 12
    assert abs(float(pca[0]["PC1_variance_percent"]) - 54.195993) < 1e-5
    assert abs(float(pca[0]["PC2_variance_percent"]) - 16.088441) < 1e-5

    for stem in (
        root / "results/figures/FigureS1_replicate_level_counts",
        root / "results/figures/FigureS2_power_analysis",
    ):
        for suffix in (".pdf", ".png", ".svg", ".tiff"):
            require_file(stem.with_suffix(suffix))
    for name in (
        "figure5_transcript_usage", "figure6_orthogonal_tiers", "figureS3_exploratory_signature",
    ):
        for suffix in (".pdf", ".png"):
            require_file(root / "docs/paper/unified_manuscript/figures" / f"{name}{suffix}")

    # H3
    raw_path = root / "results/revision/H3_power/power_simulation_raw.tsv.gz"
    assert row_count(raw_path) == 12 * 100 * (262 + 2)
    source = rows(root / "results/figures/source_data/FigureS2_power_analysis_source_data.tsv")
    assert len(source) == 2 * 5 * 12
    mde = rows(root / "results/supplement/S18_power_simulation_mde.tsv")
    assert len(mde) == 2 * 5
    assert {row["design"] for row in mde} == {
        "Discovery: genome-wide BH", "External: candidate-family BH"
    }

    # Integrated manuscript and release
    manuscript = root / "docs/paper/unified_manuscript/manuscript.md"
    manuscript_text = manuscript.read_text(encoding="utf-8")
    for marker in (
        "### 2.12 Parametric simulations", "### 5.10 Simulation-based power analysis",
        "Supplementary tables S1–S18", "Figure 6. Orthogonal evidence and final tiers",
        "Figure S1.", "Figure S2.", "Figure S3.",
    ):
        assert marker in manuscript_text, marker

    docx = root / "docs/paper/lychee_plants_revised_vixra_format_integrated.docx"
    pdf = root / "docs/paper/lychee_plants_revised_vixra_format_integrated.pdf"
    require_file(docx)
    require_file(pdf)
    with zipfile.ZipFile(docx) as archive:
        assert archive.testzip() is None and "word/document.xml" in archive.namelist()
    assert pdf.read_bytes()[:5] == b"%PDF-"

    release_dir = root / "results/release"
    bundle = release_dir / f"lychee_paper_revision_doi_bundle_{args.date}.tar.gz"
    require_file(bundle)
    assert bundle.stat().st_size < GIT_FILE_LIMIT
    with tarfile.open(bundle, "r:gz") as archive:
        names = set(archive.getnames())
        assert "lychee_paper_revision/MANIFEST.tsv" in names
        assert "lychee_paper_revision/results/supplement/S10_motif_background_tests.tsv" in names

    git_paths = current_git_paths(root)
    too_large = [(path.stat().st_size, path) for path in git_paths if path.is_file() and path.stat().st_size >= GIT_FILE_LIMIT]
    if too_large:
        raise AssertionError(f"Git-exposed files at or above 100 MB: {too_large}")
    assert root / "results/supplement/S10_motif_background_tests.tsv" not in git_paths

    print("revision_validation=PASS")
    print(f"git_exposed_files={len(git_paths)}")
    print(f"largest_git_exposed_bytes={max(path.stat().st_size for path in git_paths if path.is_file())}")
    print(f"doi_bundle_bytes={bundle.stat().st_size}")


if __name__ == "__main__":
    main()
