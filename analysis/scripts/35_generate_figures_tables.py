#!/usr/bin/env python3
"""Generate frozen figures, plotted source data, main tables, and supplements."""

from __future__ import annotations

import argparse
import hashlib
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


STUDIES = ("PRJNA450886", "PRJNA922966", "PRJNA1090613")
TIER_COLORS = {
    "Tier A": "#166534", "Tier B": "#4d7c0f", "Tier C": "#0369a1",
    "Exploratory": "#a16207", "Retired": "#991b1b",
}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column, pd.Series(index=frame.index, dtype=float)), errors="coerce")


def truth(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def placeholder(axis, message: str) -> None:
    axis.text(0.5, 0.5, message, ha="center", va="center", transform=axis.transAxes)
    axis.set_xticks([])
    axis.set_yticks([])


def panel(axis, label: str, title: str) -> None:
    axis.text(-0.12, 1.08, label, transform=axis.transAxes, fontweight="bold", fontsize=12)
    axis.set_title(title, fontsize=10)


def source_frame(frame: pd.DataFrame, panel_name: str) -> pd.DataFrame:
    result = frame.copy()
    result.insert(0, "panel", panel_name)
    return result


def save_figure(
    figure, number: int, slug: str, sources: list[pd.DataFrame],
    figure_dir: Path, source_dir: Path,
) -> list[Path]:
    basename = f"Figure{number}_{slug}"
    outputs = []
    for extension in ("pdf", "svg", "tiff"):
        path = figure_dir / f"{basename}.{extension}"
        figure.savefig(path, dpi=300 if extension == "tiff" else None, bbox_inches="tight")
        outputs.append(path)
    plt.close(figure)
    source = source_dir / f"{basename}_source_data.tsv"
    usable = [frame for frame in sources if frame is not None]
    combined = pd.concat(usable, ignore_index=True, sort=False) if usable else pd.DataFrame(
        {"panel": [], "status": []}
    )
    combined.to_csv(source, sep="\t", index=False)
    outputs.append(source)
    return outputs


def figure1(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    roles = read(root / "analysis/config/dataset_roles.tsv")
    registry = read(root / "analysis/metadata/biological_unit_registry.tsv")
    counts = registry.groupby("study", dropna=False).size().rename("registered_libraries")
    roles["registered_libraries"] = roles["study"].map(counts).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(12, 5.3))
    ax.axis("off")
    boxes = [
        (0.02, "Discovery\nPRJNA830488", "#dbeafe"),
        (0.22, "Freeze\ngenes/pathways/PWMs", "#e0e7ff"),
        (0.43, "External unlock\nPRJNA450886 then transfers", "#dcfce7"),
        (0.67, "Orthogonal\nannotation/motif/literature", "#fef3c7"),
        (0.86, "Deterministic\ntiers and claims", "#fce7f3"),
    ]
    for x, text, color in boxes:
        patch = FancyBboxPatch(
            (x, 0.60), 0.15 if x != 0.86 else 0.13, 0.22,
            boxstyle="round,pad=0.02", facecolor=color, edgecolor="#374151",
        )
        ax.add_patch(patch)
        ax.text(x + (0.075 if x != 0.86 else 0.065), 0.71, text, ha="center", va="center", fontsize=9)
    for left, right in zip(boxes[:-1], boxes[1:]):
        ax.add_patch(FancyArrowPatch(
            (left[0] + 0.15, 0.71), (right[0], 0.71),
            arrowstyle="-|>", mutation_scale=14, color="#4b5563",
        ))
    display = roles[["study", "role", "eligibility", "registered_libraries"]].copy()
    cell_text = display.astype(str).values.tolist()
    table = ax.table(
        cellText=cell_text,
        colLabels=["Study", "Locked role", "Eligibility", "Libraries"],
        cellLoc="left", colLoc="left", loc="lower center", bbox=[0.02, 0.02, 0.96, 0.42],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    ax.set_title("Study design and discovery/validation firewall", fontsize=13, pad=12)
    return save_figure(fig, 1, "study_design_firewall", [source_frame(roles, "dataset_roles")], figure_dir, source_dir)


def figure2(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    primary = root / "results/discovery/primary"
    pca = read(primary / "pca_samples.tsv")
    qc = read(root / "results/audit/PRJNA830488_technical_qc.tsv")
    all_genes = read(root / "results/discovery/all_gene_discovery_status.tsv")
    within = read(primary / "within_cultivar_contrasts.tsv")
    normalized = read(primary / "normalized_counts.tsv")
    metadata = read(root / "analysis/metadata/PRJNA830488_samples.tsv")
    frozen_ids = set(all_genes.loc[all_genes["primary_gene_status"] == "DISCOVERED", "gene_id"])

    fig, axes = plt.subplots(2, 3, figsize=(14, 8.5))
    axes = axes.ravel()
    groups = sorted(set(zip(pca.get("cultivar", []), pca.get("treatment", []))))
    colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(groups))))
    for color, group in zip(colors, groups):
        mask = (pca["cultivar"] == group[0]) & (pca["treatment"] == group[1])
        axes[0].scatter(numeric(pca.loc[mask], "PC1"), numeric(pca.loc[mask], "PC2"),
                        label="/".join(group), color=color, s=36)
    for _, row in pca.iterrows():
        axes[0].annotate(row["sample_id"], (float(row["PC1"]), float(row["PC2"])), fontsize=6)
    axes[0].legend(fontsize=6, frameon=False)
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    panel(axes[0], "A", "VST PCA")

    axes[1].bar(qc["sample_id"], numeric(qc, "star_unique_percent"), color="#2563eb")
    axes[1].axhline(40, color="#991b1b", linestyle="--", linewidth=1)
    axes[1].tick_params(axis="x", rotation=75, labelsize=6)
    axes[1].set_ylabel("Uniquely mapped reads (%)")
    panel(axes[1], "B", "Combined-reference mapping")

    q = numeric(all_genes, "interaction_q")
    lfc = numeric(all_genes, "interaction_log2fc")
    y = -np.log10(q.clip(lower=1e-300))
    discovered = all_genes["primary_gene_status"] == "DISCOVERED"
    axes[2].scatter(lfc[~discovered], y[~discovered], s=5, alpha=0.35, color="#9ca3af")
    axes[2].scatter(lfc[discovered], y[discovered], s=16, alpha=0.9, color="#dc2626")
    axes[2].axvline(math.log2(1.5), color="#4b5563", linestyle=":")
    axes[2].axvline(-math.log2(1.5), color="#4b5563", linestyle=":")
    axes[2].axhline(-math.log10(0.05), color="#4b5563", linestyle=":")
    axes[2].set_xlabel("Cultivar × infection log2 fold change")
    axes[2].set_ylabel("-log10 genome-wide q")
    panel(axes[2], "C", "Genome-wide interaction")

    pivot = within.pivot(index="gene_id", columns="contrast", values="log2fc")
    xcol, ycol = "infection_in_Guiwei", "infection_in_Yurong1"
    if xcol in pivot and ycol in pivot:
        x, yv = pd.to_numeric(pivot[xcol], errors="coerce"), pd.to_numeric(pivot[ycol], errors="coerce")
        axes[3].scatter(x, yv, s=5, alpha=0.3, color="#64748b")
        ids = pivot.index.isin(frozen_ids)
        axes[3].scatter(x[ids], yv[ids], s=18, color="#dc2626")
        limits = np.nanmax(np.abs(np.concatenate([x.values, yv.values])))
        if np.isfinite(limits):
            axes[3].plot([-limits, limits], [-limits, limits], color="#111827", linestyle="--", linewidth=0.8)
    else:
        placeholder(axes[3], "Within-cultivar contrasts unavailable")
    axes[3].set_xlabel("Guiwei infection effect")
    axes[3].set_ylabel("Yurong1 infection effect")
    panel(axes[3], "D", "Infection-effect decomposition")

    count_source = []
    if frozen_ids:
        sample_group = {
            row["sample_id"]: f"{row['cultivar']}/{row['treatment']}" for _, row in metadata.iterrows()
        }
        for _, row in normalized[normalized["gene_id"].isin(frozen_ids)].iterrows():
            for sample in normalized.columns[1:]:
                count_source.append({
                    "gene_id": row["gene_id"], "sample_id": sample,
                    "group": sample_group.get(sample, sample),
                    "normalized_count": pd.to_numeric(row[sample], errors="coerce"),
                })
    count_frame = pd.DataFrame(count_source)
    if not count_frame.empty:
        group_order = sorted(count_frame["group"].unique())
        values = [
            np.log1p(count_frame.loc[count_frame["group"] == group, "normalized_count"].dropna())
            for group in group_order
        ]
        axes[4].boxplot(values, tick_labels=group_order, showfliers=False)
        axes[4].tick_params(axis="x", rotation=35, labelsize=7)
        axes[4].set_ylabel("log1p normalized count")
    else:
        placeholder(axes[4], "No frozen gene discovery")
    panel(axes[4], "E", "Frozen-candidate expression")

    status_counts = all_genes.loc[truth(all_genes["statistical_discovery"]), "primary_gene_status"].value_counts()
    if len(status_counts):
        axes[5].bar(status_counts.index, status_counts.values, color=["#166534" if x == "DISCOVERED" else "#991b1b" for x in status_counts.index])
        axes[5].tick_params(axis="x", rotation=30, labelsize=7)
        axes[5].set_ylabel("Candidates")
    else:
        placeholder(axes[5], "No statistical candidates")
    panel(axes[5], "F", "Uniform mapping/model gate")
    fig.tight_layout()
    sources = [
        source_frame(pca, "A_PCA"), source_frame(qc, "B_mapping"),
        source_frame(all_genes, "C_volcano_F_gate"), source_frame(within, "D_effect_scatter"),
        source_frame(count_frame, "E_normalized_counts"),
    ]
    return save_figure(fig, 2, "discovery_qc_interaction", sources, figure_dir, source_dir)


def figure3(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    robust = read(root / "results/robustness/genes/frozen_gene_robustness.tsv")
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    specs = [
        ("salmon_interaction_log2fc", "A", "FeatureCounts versus Salmon"),
        ("edgeR_interaction_log2fc", "B", "DESeq2 versus edgeR"),
    ]
    for axis, (other, label, title) in zip(axes.ravel()[:2], specs):
        if len(robust):
            x = numeric(robust, "primary_interaction_log2fc")
            y = numeric(robust, other)
            passed = robust["internal_robustness_status"] == "PASS"
            axis.scatter(x[~passed], y[~passed], color="#b91c1c", s=28, label="fail")
            axis.scatter(x[passed], y[passed], color="#15803d", s=28, label="pass")
            limits = np.nanmax(np.abs(np.concatenate([x.values, y.values])))
            if np.isfinite(limits):
                axis.plot([-limits, limits], [-limits, limits], linestyle="--", color="#4b5563")
            axis.legend(frameon=False, fontsize=7)
        else:
            placeholder(axis, "No frozen genes")
        axis.set_xlabel("Primary interaction log2FC")
        axis.set_ylabel(other.replace("_", " "))
        panel(axis, label, title)
    if len(robust):
        x = np.arange(len(robust))
        axes[1, 0].bar(x - 0.18, numeric(robust, "loo_sign_agreement_count"), width=0.36, label="sign")
        axes[1, 0].bar(x + 0.18, numeric(robust, "loo_q_below_threshold_count"), width=0.36, label="q")
        axes[1, 0].set_xticks(x, robust["gene_id"], rotation=75, fontsize=6)
        axes[1, 0].legend(frameon=False, fontsize=7)
    else:
        placeholder(axes[1, 0], "No frozen genes")
    panel(axes[1, 0], "C", "Leave-one-library-out stability")
    if len(robust):
        status = robust["observed_mapping_sensitivity_status"].value_counts()
        axes[1, 1].bar(status.index, status.values, color="#0f766e")
        axes[1, 1].tick_params(axis="x", rotation=35, labelsize=7)
    else:
        placeholder(axes[1, 1], "No mapping sensitivity candidates")
    panel(axes[1, 1], "D", "Observed mapping sensitivity")
    fig.tight_layout()
    return save_figure(
        fig, 3, "internal_robustness", [source_frame(robust, "A_D_gene_robustness")],
        figure_dir, source_dir,
    )


def external_frames(root: Path, subdir: str, filename: str) -> pd.DataFrame:
    frames = []
    for study in STUDIES:
        path = root / "results/external" / study / subdir / filename
        if path.exists():
            frame = read(path)
            if "study" not in frame:
                frame["study"] = study
            frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def figure4(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    genes = external_frames(root, "genes", "frozen_gene_tests.tsv")
    signatures = external_frames(root, "genes", "signature_contrasts.tsv")
    primary = genes[(genes.get("study", "") == "PRJNA450886") & (genes.get("contrast", "") == "primary_24h")].copy()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    if len(primary):
        primary = primary.sort_values("external_q", key=lambda x: pd.to_numeric(x, errors="coerce")).head(30)
        y = np.arange(len(primary))
        effect = numeric(primary, "external_log2fc")
        lower, upper = numeric(primary, "confidence_lower"), numeric(primary, "confidence_upper")
        color = primary["external_status"].map({
            "cross_context_supported": "#15803d", "contradictory": "#b91c1c",
            "unsupported": "#a16207", "not_testable": "#6b7280",
        }).fillna("#6b7280")
        axes[0, 0].errorbar(effect, y, xerr=[effect - lower, upper - effect], fmt="none", ecolor="#9ca3af")
        axes[0, 0].scatter(effect, y, c=color, s=28)
        axes[0, 0].set_yticks(y, primary["gene_id"], fontsize=6)
        axes[0, 0].axvline(0, color="#111827", linewidth=0.8)
    else:
        placeholder(axes[0, 0], "No frozen gene is externally testable")
    panel(axes[0, 0], "A", "PRJNA450886 24-h frozen-gene forest")

    temporal = genes[genes.get("study", "") == "PRJNA450886"].copy()
    if len(temporal):
        grouped = temporal.groupby("contrast")["external_status"].value_counts().unstack(fill_value=0)
        grouped.plot(kind="bar", stacked=True, ax=axes[0, 1], colormap="Set2", legend=True)
        axes[0, 1].tick_params(axis="x", rotation=30, labelsize=7)
        axes[0, 1].legend(fontsize=6, frameon=False)
    else:
        placeholder(axes[0, 1], "No temporal tests")
    panel(axes[0, 1], "B", "6/24/48-h evidence labels")

    if len(signatures):
        sig = signatures.copy()
        sig["label"] = sig["study"].astype(str) + "/" + sig["contrast"].astype(str)
        estimate = numeric(sig, "estimate")
        lower, upper = numeric(sig, "confidence_lower"), numeric(sig, "confidence_upper")
        y = np.arange(len(sig))
        axes[1, 0].errorbar(estimate, y, xerr=[estimate - lower, upper - estimate], fmt="o", color="#0369a1", ecolor="#93c5fd")
        axes[1, 0].set_yticks(y, sig["label"], fontsize=6)
        axes[1, 0].axvline(0, color="#111827", linewidth=0.8)
    else:
        placeholder(axes[1, 0], "Frozen signature not testable")
    panel(axes[1, 0], "C", "Frozen-signature contrasts")

    if len(genes):
        cross = genes.groupby("study")["external_status"].value_counts().unstack(fill_value=0)
        cross.plot(kind="bar", stacked=True, ax=axes[1, 1], colormap="RdYlGn", legend=True)
        axes[1, 1].tick_params(axis="x", rotation=25, labelsize=7)
        axes[1, 1].legend(fontsize=6, frameon=False)
    else:
        placeholder(axes[1, 1], "No external gene results")
    panel(axes[1, 1], "D", "Cross-study frozen-gene outcomes")
    fig.tight_layout()
    return save_figure(
        fig, 4, "external_cross_context",
        [source_frame(genes, "A_B_D_external_genes"), source_frame(signatures, "C_signatures")],
        figure_dir, source_dir,
    )


def figure5(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    pathways = external_frames(root, "pathways", "frozen_pathway_tests.tsv")
    signatures = external_frames(root, "genes", "signature_contrasts.tsv")
    primary = pathways[pathways.get("study", "") == "PRJNA450886"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    if len(primary):
        x, y = numeric(primary, "discovery_NES"), numeric(primary, "fgsea_NES")
        axes[0].scatter(x, y, c=primary["external_pathway_status"].map(
            {"cross_context_supported": "#15803d", "unsupported": "#a16207", "not_testable": "#6b7280"}
        ).fillna("#6b7280"))
        axes[0].axhline(0, color="#9ca3af", linewidth=0.7)
        axes[0].axvline(0, color="#9ca3af", linewidth=0.7)
    else:
        placeholder(axes[0], "No frozen pathway")
    axes[0].set_xlabel("Discovery NES")
    axes[0].set_ylabel("External fgsea NES")
    panel(axes[0], "A", "Pathway direction transport")
    if len(primary):
        percentile = numeric(primary, "empirical_percentile")
        axes[1].bar(primary["pathway"], percentile, color="#0f766e")
        axes[1].axhline(0.95, color="#991b1b", linestyle="--")
        axes[1].tick_params(axis="x", rotation=75, labelsize=6)
    else:
        placeholder(axes[1], "Matched null not applicable")
    axes[1].set_ylabel("Matched-null percentile")
    panel(axes[1], "B", "Matched-set specificity")
    if len(signatures):
        labels = signatures["study"].astype(str) + "/" + signatures["contrast"].astype(str)
        estimate = numeric(signatures, "estimate")
        axes[2].barh(labels, estimate, color=["#15803d" if value > 0 else "#b91c1c" for value in estimate.fillna(0)])
        axes[2].axvline(0, color="#111827", linewidth=0.8)
        axes[2].tick_params(axis="y", labelsize=6)
    else:
        placeholder(axes[2], "Frozen signature not testable")
    panel(axes[2], "C", "Frozen signed signature")
    fig.tight_layout()
    return save_figure(
        fig, 5, "pathway_signature_validation",
        [source_frame(pathways, "A_B_pathways"), source_frame(signatures, "C_signatures")],
        figure_dir, source_dir,
    )


def figure6(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    dtu = read(root / "results/discovery/dtu/all_dtu_results.tsv")
    frozen = read(root / "results/discovery/frozen_dtu.tsv")
    if frozen.empty:
        omitted = figure_dir / "Figure6_OMITTED.txt"
        omitted.write_text(
            "The frozen conditional DTU gate yielded no eligible discovery; Figure 6 is omitted prospectively.\n"
        )
        source = source_dir / "Figure6_OMITTED_source_data.tsv"
        read(root / "results/discovery/dtu/dtu_gate.tsv").to_csv(source, sep="\t", index=False)
        return [omitted, source]
    external = external_frames(root, "dtu", "frozen_dtu_external_tests.tsv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    qcol = "gene_q" if "gene_q" in dtu else "q"
    effect_col = "maximum_absolute_delta_proportion" if "maximum_absolute_delta_proportion" in dtu else "interaction_effect"
    axes[0].scatter(numeric(dtu, effect_col), -np.log10(numeric(dtu, qcol).clip(lower=1e-300)), s=8, alpha=0.4)
    axes[0].set_xlabel(effect_col.replace("_", " "))
    axes[0].set_ylabel("-log10 q")
    panel(axes[0], "A", "Conditional transcript-usage discovery")
    if len(external) and "external_dtu_status" in external:
        status = external["external_dtu_status"].value_counts()
        axes[1].bar(status.index, status.values, color="#7c3aed")
        axes[1].tick_params(axis="x", rotation=30)
    else:
        placeholder(axes[1], "External DTU not testable")
    panel(axes[1], "B", "Frozen external DTU")
    fig.tight_layout()
    return save_figure(
        fig, 6, "conditional_dtu",
        [source_frame(dtu, "A_discovery_DTU"), source_frame(external, "B_external_DTU")],
        figure_dir, source_dir,
    )


def figure7(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    annotation = read(root / "results/evidence/annotation/final_candidate_annotations.tsv")
    small = read(root / "results/evidence/small_rna/reference/small_rna_reference_gate.tsv")
    discovery_motifs = read(root / "results/evidence/motifs/results/robust_candidate_motifs.tsv")
    external_motifs = read(root / "results/external/PRJNA450886/motifs/transport/external_motif_transport.tsv")
    published = read(root / "results/evidence/published_evidence_registry.tsv")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    counts = annotation["annotation_status"].value_counts() if len(annotation) else pd.Series(dtype=int)
    if len(counts):
        axes[0, 0].bar(counts.index, counts.values, color="#2563eb")
        axes[0, 0].tick_params(axis="x", rotation=30, labelsize=7)
    else:
        placeholder(axes[0, 0], "No frozen candidate")
    panel(axes[0, 0], "A", "Annotation evidence")
    small_label = small.iloc[0]["reference_gate_status"] if len(small) else "MISSING"
    axes[0, 1].text(0.5, 0.58, small_label, ha="center", va="center", wrap=True, fontsize=11)
    axes[0, 1].text(0.5, 0.35, "condition-level coherence only", ha="center", va="center", fontsize=8)
    axes[0, 1].set_axis_off()
    panel(axes[0, 1], "B", "Small-RNA gate")
    motif_counts = pd.Series({
        "discovery robust": int((discovery_motifs.get("discovery_motif_status", pd.Series(dtype=str)) == "ROBUST_CANDIDATE_MOTIF").sum()),
        "externally transported": int((external_motifs.get("external_motif_transport_status", pd.Series(dtype=str)) == "cross_context_supported").sum()),
    })
    axes[1, 0].bar(motif_counts.index, motif_counts.values, color=["#7c3aed", "#15803d"])
    axes[1, 0].tick_params(axis="x", rotation=20, labelsize=7)
    panel(axes[1, 0], "C", "Candidate motif robustness/transport")
    pub_counts = published["independent_of_current_datasets"].str.lower().value_counts()
    axes[1, 1].bar(pub_counts.index, pub_counts.values, color="#a16207")
    axes[1, 1].set_ylabel("Registered sources")
    panel(axes[1, 1], "D", "Published-evidence independence")
    fig.tight_layout()
    return save_figure(
        fig, 7, "orthogonal_support",
        [
            source_frame(annotation, "A_annotation"), source_frame(small, "B_small_RNA"),
            source_frame(discovery_motifs, "C_discovery_motifs"),
            source_frame(external_motifs, "C_external_motifs"),
            source_frame(published, "D_published"),
        ], figure_dir, source_dir,
    )


def figure8(root: Path, figure_dir: Path, source_dir: Path) -> list[Path]:
    evidence = read(root / "results/candidates/final_evidence_matrix.tsv")
    fig_height = max(4.5, min(14, 0.32 * max(1, len(evidence)) + 2))
    fig, ax = plt.subplots(figsize=(11, fig_height))
    columns = ["Discovery", "Robustness", "External", "Orthogonal", "Tier"]
    values = []
    labels = []
    tier_numeric = {"Tier A": 1.0, "Tier B": 0.7, "Tier C": 0.5, "Exploratory": 0.0, "Retired": -1.0}
    for _, row in evidence.iterrows():
        discovery = 1.0 if row["discovery_status"] in {"DISCOVERED", "FROZEN_PATHWAY"} else -1.0
        robust = 1.0 if row["internal_robustness_status"] == "PASS" else -1.0
        external = {
            "cross_context_supported": 1.0, "partial": 0.4, "not_testable": 0.0,
            "unsupported": -0.4, "contradictory": -1.0,
        }.get(row["external_status"], 0.0)
        orthogonal = 1.0 if float(row["orthogonal_class_count"] or 0) > 0 else 0.0
        values.append([discovery, robust, external, orthogonal, tier_numeric[row["final_tier"]]])
        labels.append(f"{row['entity_type']}:{row['entity_id']}")
    if values:
        matrix = np.array(values)
        cmap = ListedColormap(["#991b1b", "#fef3c7", "#166534"])
        ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=-1, vmax=1)
        ax.set_xticks(range(len(columns)), columns)
        ax.set_yticks(range(len(labels)), labels, fontsize=6)
        for i, row in evidence.reset_index(drop=True).iterrows():
            texts = [
                row["discovery_status"], row["internal_robustness_status"],
                row["external_status"], str(row["orthogonal_class_count"]), row["final_tier"],
            ]
            for j, text in enumerate(texts):
                ax.text(j, i, text, ha="center", va="center", fontsize=5.5)
    else:
        placeholder(ax, "No frozen gene or pathway candidates")
    ax.set_title("Final evidence matrix: separate layers and deterministic tiers")
    fig.tight_layout()
    return save_figure(
        fig, 8, "final_evidence_matrix", [source_frame(evidence, "evidence_matrix")],
        figure_dir, source_dir,
    )


def copy_table(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def manifest_frame(paths: list[Path], root: Path) -> pd.DataFrame:
    return pd.DataFrame([
        {"path": str(path.relative_to(root)), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(paths) if path.is_file()
    ])


def generate_tables(root: Path, table_dir: Path, supplement_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    outputs.append(copy_table(root / "analysis/config/dataset_roles.tsv", table_dir / "Table1_dataset_roles_eligibility.tsv"))

    genes = read(root / "results/discovery/all_gene_discovery_status.tsv")
    genes = genes[truth(genes["statistical_discovery"])].copy()
    genes.insert(0, "entity_type", "gene")
    pathways = read(root / "results/discovery/frozen_pathways.tsv")
    pathways.insert(0, "entity_type", "pathway")
    table2 = pd.concat([genes, pathways], ignore_index=True, sort=False)
    table2_path = table_dir / "Table2_frozen_discovery.tsv"
    table2.to_csv(table2_path, sep="\t", index=False)
    outputs.append(table2_path)

    robust_genes = read(root / "results/robustness/genes/frozen_gene_robustness.tsv")
    robust_genes.insert(0, "entity_type", "gene")
    robust_pathways = read(root / "results/robustness/pathways/frozen_pathway_robustness.tsv")
    robust_pathways.insert(0, "entity_type", "pathway")
    table3_path = table_dir / "Table3_internal_robustness.tsv"
    pd.concat([robust_genes, robust_pathways], ignore_index=True, sort=False).to_csv(
        table3_path, sep="\t", index=False
    )
    outputs.append(table3_path)

    external_genes = external_frames(root, "genes", "frozen_gene_tests.tsv")
    external_genes.insert(0, "entity_type", "gene")
    external_pathways = external_frames(root, "pathways", "frozen_pathway_tests.tsv")
    external_pathways.insert(0, "entity_type", "pathway")
    table4_path = table_dir / "Table4_external_evaluation.tsv"
    pd.concat([external_genes, external_pathways], ignore_index=True, sort=False).to_csv(
        table4_path, sep="\t", index=False
    )
    outputs.append(table4_path)
    outputs.append(copy_table(
        root / "results/candidates/final_evidence_matrix.tsv",
        table_dir / "Table5_orthogonal_final_status.tsv",
    ))

    outputs.append(copy_table(
        root / "analysis/metadata/biological_unit_registry.tsv",
        supplement_dir / "S1_biological_unit_registry.tsv",
    ))
    outputs.append(copy_table(
        root / "results/audit/PRJNA830488_technical_qc.tsv",
        supplement_dir / "S2_per_library_QC.tsv",
    ))
    outputs.append(copy_table(
        root / "results/discovery/all_gene_discovery_status.tsv",
        supplement_dir / "S3_all_discovery_statistics.tsv",
    ))
    robustness_files = list((root / "results/robustness").rglob("*"))
    s4 = supplement_dir / "S4_robustness_file_manifest.tsv"
    manifest_frame(robustness_files, root).to_csv(s4, sep="\t", index=False)
    outputs.append(s4)
    external_parts = []
    for study in STUDIES:
        for subtype, filename in (
            ("gene", "genes/frozen_gene_tests.tsv"),
            ("pathway", "pathways/frozen_pathway_tests.tsv"),
            ("dtu", "dtu/frozen_dtu_external_tests.tsv"),
        ):
            path = root / "results/external" / study / filename
            if path.exists():
                frame = read(path)
                frame.insert(0, "evidence_type", subtype)
                if "study" not in frame:
                    frame.insert(1, "study", study)
                external_parts.append(frame)
    s5 = supplement_dir / "S5_all_external_frozen_tests.tsv"
    pd.concat(external_parts, ignore_index=True, sort=False).to_csv(s5, sep="\t", index=False)
    outputs.append(s5)
    pathway_signature_parts = []
    for study in STUDIES:
        for subtype, filename in (
            ("pathway", "pathways/frozen_pathway_tests.tsv"),
            ("signature", "genes/signature_contrasts.tsv"),
        ):
            path = root / "results/external" / study / filename
            if path.exists():
                frame = read(path)
                frame.insert(0, "evidence_type", subtype)
                if "study" not in frame:
                    frame.insert(1, "study", study)
                pathway_signature_parts.append(frame)
    s6 = supplement_dir / "S6_pathway_signature_tests.tsv"
    pd.concat(pathway_signature_parts, ignore_index=True, sort=False).to_csv(s6, sep="\t", index=False)
    outputs.append(s6)
    outputs.append(copy_table(
        root / "results/discovery/dtu/all_dtu_results.tsv",
        supplement_dir / "S7_DTU_results.tsv",
    ))
    outputs.append(copy_table(
        root / "results/evidence/annotation/final_candidate_annotations.tsv",
        supplement_dir / "S8_annotation_orthology.tsv",
    ))
    outputs.append(copy_table(
        root / "results/evidence/small_rna/reference/small_rna_reference_gate.tsv",
        supplement_dir / "S9_small_RNA_results.tsv",
    ))
    motif_parts = []
    motif_paths = [
        root / "results/evidence/motifs/results/ame_matched_background_replicates.tsv",
        root / "results/evidence/motifs/results/fimo_matched_background_sensitivity.tsv",
        root / "results/evidence/motifs/results/candidate_motif_site_presence.tsv",
        root / "results/external/PRJNA450886/motifs/transport/external_ame_replicates.tsv",
        root / "results/external/PRJNA450886/motifs/transport/external_fimo_sensitivity.tsv",
    ]
    for path in motif_paths:
        if path.exists():
            frame = read(path)
            frame.insert(0, "source_file", str(path.relative_to(root)))
            motif_parts.append(frame)
    s10 = supplement_dir / "S10_motif_background_tests.tsv"
    pd.concat(motif_parts, ignore_index=True, sort=False).to_csv(s10, sep="\t", index=False)
    outputs.append(s10)
    outputs.append(copy_table(
        root / "results/evidence/published_evidence_registry.tsv",
        supplement_dir / "S11_evidence_registry.tsv",
    ))
    code_files = [
        *list((root / "analysis/scripts").glob("*")),
        *list((root / "analysis/workflow").glob("*")),
        *list((root / "analysis/envs").glob("*")),
        *list((root / "analysis/config").glob("*")),
        root / "results/audit/software_sessionInfo.txt",
    ]
    s12 = supplement_dir / "S12_scripts_environments_commands.tsv"
    manifest_frame(code_files, root).to_csv(s12, sep="\t", index=False)
    outputs.append(s12)
    outputs.append(copy_table(
        root / "analysis/preregistration/amendments.tsv",
        supplement_dir / "S13_amendment_deviation_log.tsv",
    ))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--figure-dir", type=Path, default=Path("results/figures"))
    parser.add_argument("--table-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--supplement-dir", type=Path, default=Path("results/supplement"))
    args = parser.parse_args()
    root = args.root.resolve()
    figure_dir = (root / args.figure_dir).resolve()
    table_dir = (root / args.table_dir).resolve()
    supplement_dir = (root / args.supplement_dir).resolve()
    source_dir = figure_dir / "source_data"
    for directory in (figure_dir, source_dir, table_dir, supplement_dir):
        directory.mkdir(parents=True, exist_ok=True)

    figure_outputs = []
    for function in (figure1, figure2, figure3, figure4, figure5, figure6, figure7, figure8):
        figure_outputs.extend(function(root, figure_dir, source_dir))
    table_outputs = generate_tables(root, table_dir, supplement_dir)
    figure_manifest = figure_dir / "figures.sha256"
    table_manifest = table_dir / "tables_supplements.sha256"
    with figure_manifest.open("w") as handle:
        for path in sorted(figure_outputs):
            handle.write(f"{sha256(path)}  {path.relative_to(root)}\n")
    with table_manifest.open("w") as handle:
        for path in sorted(table_outputs):
            handle.write(f"{sha256(path)}  {path.relative_to(root)}\n")
    print(
        f"report assets: {len(figure_outputs)} figure/source artifacts; "
        f"{len(table_outputs)} table/supplement artifacts"
    )


if __name__ == "__main__":
    main()
