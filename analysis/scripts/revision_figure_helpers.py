"""Reviewer-response supplementary figure generation for script 35."""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _save(
    figure: plt.Figure,
    basename: str,
    source: pd.DataFrame,
    figure_dir: Path,
    source_dir: Path,
) -> list[Path]:
    outputs: list[Path] = []
    for extension in ("pdf", "svg", "tiff", "png"):
        path = figure_dir / f"{basename}.{extension}"
        figure.savefig(
            path,
            dpi=300 if extension in {"tiff", "png"} else None,
            bbox_inches="tight",
        )
        outputs.append(path)
    plt.close(figure)
    source_path = source_dir / f"{basename}_source_data.tsv"
    source.to_csv(source_path, sep="\t", index=False)
    outputs.append(source_path)
    return outputs


def _pca_source(root: Path, source_dir: Path) -> Path:
    """Attach variance fractions to the existing, frozen PCA coordinates."""
    pca = _read(root / "results/discovery/primary/pca_samples.tsv")
    vst = _read(root / "results/discovery/primary/vst_expression.tsv")
    sample_columns = [column for column in vst.columns if column != "gene_id"]
    if len(pca) != 12 or len(sample_columns) != 12:
        raise AssertionError("H6 expects 12 discovery PCA samples")
    matrix = vst[sample_columns].apply(pd.to_numeric, errors="raise").to_numpy().T.copy()
    matrix -= matrix.mean(axis=0, keepdims=True)
    singular_values = np.linalg.svd(matrix, full_matrices=False, compute_uv=False)
    fractions = singular_values**2 / np.sum(singular_values**2)
    pc1 = 100.0 * float(fractions[0])
    pc2 = 100.0 * float(fractions[1])
    if not (0 < pc2 < pc1 < 100 and pc1 + pc2 < 100):
        raise AssertionError(f"Unexpected PCA variance fractions: {pc1}, {pc2}")
    pca["PC1_variance_percent"] = pc1
    pca["PC2_variance_percent"] = pc2
    output = source_dir / "UnifiedFigure1_PCA_source_data.tsv"
    pca.to_csv(output, sep="\t", index=False)
    return output


def _replicate_count_figure(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    normalized = _read(root / "results/discovery/primary/normalized_counts.tsv")
    metadata = _read(root / "analysis/metadata/PRJNA830488_samples.tsv")
    tiers = _read(root / "results/tables/Table5_orthogonal_final_status.tsv")
    external = _read(root / "results/tables/Table4_external_evaluation.tsv")

    supported = sorted(
        set(
            external.loc[
                (external["entity_type"] == "gene")
                & (external["study"] == "PRJNA450886")
                & (external["contrast"] == "primary_24h")
                & (external["external_status"] == "cross_context_supported"),
                "gene_id",
            ]
        )
    )
    tier_b = sorted(
        set(
            tiers.loc[
                (tiers["entity_type"] == "gene") & (tiers["final_tier"] == "Tier B"),
                "entity_id",
            ]
        )
    )
    legacy = ["LITCHI001510", "LITCHI019519"]
    if len(supported) != 2 or len(tier_b) != 12:
        raise AssertionError(
            f"Expected 2 supported and 12 Tier B genes; got {len(supported)} and {len(tier_b)}"
        )
    if set(supported) & set(tier_b) or (set(supported) | set(tier_b)) & set(legacy):
        raise AssertionError("H4 gene groups must be disjoint")

    categories = {
        **{gene: "Cross-context supported" for gene in supported},
        **{gene: "Tier B" for gene in tier_b},
        **{gene: "Legacy highlight" for gene in legacy},
    }
    selected = supported + tier_b + legacy
    selected_counts = normalized[normalized["gene_id"].isin(selected)].copy()
    if len(selected_counts) != 16:
        raise AssertionError(f"Expected normalized counts for 16 genes, found {len(selected_counts)}")

    meta = metadata.set_index("sample_id")
    records: list[dict[str, object]] = []
    for _, row in selected_counts.iterrows():
        gene = str(row["gene_id"])
        for sample in normalized.columns[1:]:
            if sample not in meta.index:
                raise AssertionError(f"Missing discovery metadata for {sample}")
            count = float(row[sample])
            info = meta.loc[sample]
            records.append(
                {
                    "gene_id": gene,
                    "evidence_group": categories[gene],
                    "sample_id": sample,
                    "cultivar": info["cultivar"],
                    "treatment": info["treatment"],
                    "replicate": info["replicate"],
                    "normalized_count": count,
                    "log2_normalized_count_plus_1": np.log2(count + 1.0),
                }
            )
    source = pd.DataFrame(records)
    if len(source) != 16 * 12 or source["normalized_count"].isna().any():
        raise AssertionError("Incomplete H4 replicate-count source data")

    group_order = [
        ("Guiwei", "mock"),
        ("Guiwei", "infected"),
        ("Yurong1", "mock"),
        ("Yurong1", "infected"),
    ]
    group_labels = ["GW\nmock", "GW\ninf.", "YR\nmock", "YR\ninf."]
    color = {"Guiwei": "#0072B2", "Yurong1": "#E69F00"}
    marker = {"mock": "o", "infected": "^"}
    category_order = ["Cross-context supported", "Tier B", "Legacy highlight"]
    ordered_genes = [
        gene
        for category in category_order
        for gene in selected
        if categories[gene] == category
    ]
    figure, axes = plt.subplots(4, 4, figsize=(11.5, 10.5), constrained_layout=True)
    rng = np.random.default_rng(20260718)
    for axis, gene in zip(axes.ravel(), ordered_genes):
        gene_data = source[source["gene_id"] == gene]
        for x, (cultivar, treatment) in enumerate(group_order):
            subset = gene_data[
                (gene_data["cultivar"] == cultivar) & (gene_data["treatment"] == treatment)
            ]
            values = subset["log2_normalized_count_plus_1"].to_numpy(float)
            if len(values) != 3:
                raise AssertionError(f"Expected 3 replicates for {gene} {cultivar}/{treatment}")
            jitter = rng.uniform(-0.08, 0.08, len(values))
            axis.scatter(
                np.full(len(values), x) + jitter,
                values,
                color=color[cultivar],
                marker=marker[treatment],
                edgecolor="white",
                linewidth=0.45,
                s=32,
                zorder=3,
            )
            axis.plot([x - 0.16, x + 0.16], [np.median(values)] * 2, color="#222222", lw=1.1)
        axis.set_xticks(range(4), group_labels, fontsize=6.5)
        axis.set_title(f"{gene}\n{categories[gene]}", fontsize=7.4)
        axis.grid(axis="y", color="#E8E8E8", linewidth=0.5)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    for axis in axes[:, 0]:
        axis.set_ylabel("log2(norm. count + 1)", fontsize=7)
    figure.suptitle(
        "Discovery-cohort replicate-level expression for headline genes",
        fontsize=12,
        fontweight="bold",
    )
    return _save(figure, "FigureS1_replicate_level_counts", source, figure_dir, source_dir)


def generate_revision_figures(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    """Generate H4/H6 artifacts and a separate checksum manifest."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    outputs = [_pca_source(root, source_dir)]
    outputs.extend(_replicate_count_figure(root, figure_dir, source_dir))
    manifest = figure_dir / "revision_figures.sha256"
    with manifest.open("w", encoding="utf-8") as handle:
        for path in sorted(outputs):
            handle.write(f"{_sha256(path)}  {path.relative_to(root)}\n")
    outputs.append(manifest)
    return outputs
