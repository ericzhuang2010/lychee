#!/usr/bin/env python3
"""Build the unified manuscript figures from frozen tabular results.

The plotting code intentionally recomputes every displayed count from the TSV
files and asserts the manuscript's headline values.  It uses only Python's
standard library, NumPy, and Matplotlib; pandas is not required.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch

from h7_split_figures import generate_h7_figures


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "figures"

# Okabe-Ito-inspired palette; every contrast remains distinct in common forms
# of colour-vision deficiency and is reinforced by symbols, outlines, or text.
BLUE = "#0072B2"
SKY = "#56B4E9"
GREEN = "#009E73"
ORANGE = "#E69F00"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
GRAY = "#777777"
LIGHT_GRAY = "#D9D9D9"
DARK = "#222222"
WHITE = "#FFFFFF"


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.2,
        "axes.linewidth": 0.7,
        "lines.linewidth": 1.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def read_tsv(relative_path: str) -> list[dict[str, str]]:
    path = ROOT / relative_path
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def number(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value in {"", "NA", "NaN", "nan"}:
        return math.nan
    return float(value)


def yes(row: dict[str, str], key: str) -> bool:
    return row.get(key, "").upper() == "TRUE"


def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.set_title(title, loc="left", pad=8)
    ax.text(
        -0.08,
        1.035,
        letter,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def clean_axes(ax: plt.Axes, grid_axis: str | None = None) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color="#E8E8E8", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def add_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    facecolor: str,
    edgecolor: str = "none",
    fontsize: float = 8.0,
) -> None:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=0.9,
        transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=DARK,
    )


def figure1_cohorts_qc() -> None:
    registry = read_tsv("analysis/metadata/biological_unit_registry.tsv")
    counts = Counter(row["study"] for row in registry)
    expected = {
        "PRJNA830488": 12,
        "PRJNA450886": 36,
        "PRJNA922966": 12,
        "PRJNA922965": 12,
        "PRJNA1090613": 12,
    }
    assert counts == expected, (counts, expected)

    source = read_tsv(
        "results/figures/source_data/Figure2_discovery_qc_interaction_source_data.tsv"
    )
    pca = read_tsv("results/figures/source_data/UnifiedFigure1_PCA_source_data.tsv")
    mapping = [row for row in source if row["panel"] == "B_mapping"]
    assert len(pca) == 12 and len(mapping) == 12
    assert Counter(row["technical_gate"] for row in mapping) == {"INCLUDE": 12}
    pc1_variance = number(pca[0], "PC1_variance_percent")
    pc2_variance = number(pca[0], "PC2_variance_percent")
    assert all(math.isclose(number(row, "PC1_variance_percent"), pc1_variance) for row in pca)
    assert all(math.isclose(number(row, "PC2_variance_percent"), pc2_variance) for row in pca)

    fig = plt.figure(figsize=(8.2, 7.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.18])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, :])

    studies = [
        "PRJNA830488",
        "PRJNA450886",
        "PRJNA922966",
        "PRJNA922965",
        "PRJNA1090613",
    ]
    labels = [
        "Discovery\nGuiwei / Yurong1 leaf",
        "Primary cross-context\nGuiwei / Heiye pericarp",
        "Generic transfer\nFeizixiao leaf / fruit",
        "Orthogonal small RNA\nFeizixiao leaf / fruit",
        "Exploratory\nGuiwei / SFZ leaf",
    ]
    colors = [BLUE, ORANGE, GREEN, PURPLE, GRAY]
    values = [counts[study] for study in studies]
    y = np.arange(len(studies))
    ax_a.barh(y, values, color=colors, height=0.64, zorder=2)
    for yi, value, study in zip(y, values, studies):
        ax_a.text(value + 0.8, yi, f"{value} libraries", va="center", fontsize=7.3)
        ax_a.text(0.6, yi, study, va="center", ha="left", color=WHITE, fontsize=7.2)
    ax_a.set_yticks(y, labels)
    ax_a.invert_yaxis()
    ax_a.set_xlim(0, 43)
    ax_a.set_xlabel("Deposited libraries")
    panel_title(ax_a, "A", "Cohort roles and deposited libraries")
    clean_axes(ax_a, "x")

    metrics = [
        ("fastp survival", [100 * number(r, "fastp_survival_fraction") for r in mapping]),
        ("STAR unique", [number(r, "star_unique_percent") for r in mapping]),
        ("Salmon mapping", [100 * number(r, "salmon_mapping_rate") for r in mapping]),
    ]
    rng = np.random.default_rng(830488)
    for xi, (label, values_i) in enumerate(metrics):
        jitter = rng.uniform(-0.08, 0.08, len(values_i))
        ax_b.scatter(
            np.full(len(values_i), xi) + jitter,
            values_i,
            color=BLUE,
            edgecolor=WHITE,
            linewidth=0.45,
            s=25,
            zorder=3,
        )
        ax_b.plot([xi - 0.14, xi + 0.14], [np.mean(values_i)] * 2, color=DARK, lw=1.4)
        ax_b.text(
            xi,
            min(values_i) - 1.6,
            f"{min(values_i):.2f}–{max(values_i):.2f}%",
            ha="center",
            va="top",
            fontsize=6.8,
        )
    ax_b.set_xticks(range(3), [item[0] for item in metrics])
    ax_b.set_ylabel("Reads or alignments (%)")
    ax_b.set_ylim(76, 101.5)
    ax_b.text(
        0.98,
        0.95,
        "12/12 libraries included",
        transform=ax_b.transAxes,
        ha="right",
        va="top",
        color=GREEN,
        fontweight="bold",
    )
    panel_title(ax_b, "B", "Discovery technical QC")
    clean_axes(ax_b, "y")

    cultivar_color = {"Guiwei": BLUE, "Yurong1": ORANGE}
    treatment_marker = {"mock": "o", "infected": "^"}
    for row in pca:
        ax_c.scatter(
            number(row, "PC1"),
            number(row, "PC2"),
            color=cultivar_color[row["cultivar"]],
            marker=treatment_marker[row["treatment"]],
            s=58,
            edgecolor=DARK,
            linewidth=0.55,
            zorder=3,
        )
    ax_c.axhline(0, color=LIGHT_GRAY, lw=0.6, zorder=0)
    ax_c.axvline(0, color=LIGHT_GRAY, lw=0.6, zorder=0)
    ax_c.set_xlabel(f"PC1 ({pc1_variance:.1f}% variance)")
    ax_c.set_ylabel(f"PC2 ({pc2_variance:.1f}% variance)")
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE,
               markeredgecolor=DARK, label="Guiwei", markersize=6),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE,
               markeredgecolor=DARK, label="Yurong1", markersize=6),
        Line2D([0], [0], marker="o", color=DARK, markerfacecolor=WHITE,
               linestyle="none", label="Mock", markersize=6),
        Line2D([0], [0], marker="^", color=DARK, markerfacecolor=WHITE,
               linestyle="none", label="Infected", markersize=6),
    ]
    ax_c.legend(handles=legend, ncol=4, loc="upper center", frameon=False)
    panel_title(ax_c, "C", "Expression PCA separates cultivar and infection response")
    clean_axes(ax_c)
    save_figure(fig, "figure1_study_design_qc")


def figure2_discovery_legacy() -> None:
    stats = read_tsv("results/supplement/S3_all_discovery_statistics.tsv")
    legacy = read_tsv("results/discovery/primary/legacy_18_audit.tsv")
    assert len(stats) == 19_445
    status_counts = Counter(row["primary_gene_status"] for row in stats)
    assert sum(yes(row, "statistical_discovery") for row in stats) == 262
    assert status_counts["DISCOVERED"] == 206
    assert status_counts["RETIRED_MAPPING_FAILURE"] == 31
    assert status_counts["RETIRED_GENE_MODEL_AMBIGUITY"] == 25
    assert len(legacy) == 18
    assert sum(number(row, "interaction_q") < 0.05 for row in legacy) == 0
    by_gene = {row["gene_id"]: row for row in stats}
    legacy_joined = [(row, by_gene[row["gene_id"]]) for row in legacy]
    assert sum(joined["mappability_status"] == "FAIL" for _, joined in legacy_joined) == 2

    robust_rows = [
        row
        for row in read_tsv("results/tables/Table3_internal_robustness.tsv")
        if row["entity_type"] == "gene"
    ]
    assert sum(row["internal_robustness_status"] == "PASS" for row in robust_rows) == 16
    external = [
        row
        for row in read_tsv("results/tables/Table4_external_evaluation.tsv")
        if row["entity_type"] == "gene"
        and row["study"] == "PRJNA450886"
        and row["contrast"] == "primary_24h"
    ]
    supported = {
        row["gene_id"] for row in external if row["external_status"] == "cross_context_supported"
    }
    robust = {
        row["gene_id"] for row in robust_rows if row["internal_robustness_status"] == "PASS"
    }
    assert len(supported) == 2 and robust.isdisjoint(supported)

    fig = plt.figure(figsize=(8.4, 7.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.12, 1.25], width_ratios=[1.35, 1])
    ax_a = fig.add_subplot(grid[0, :])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])

    classes = [
        ("NOT_STATISTICAL_DISCOVERY", LIGHT_GRAY, 5, 0.34, "Not selected"),
        ("RETIRED_MAPPING_FAILURE", VERMILLION, 13, 0.72, "Retired: mappability"),
        ("RETIRED_GENE_MODEL_AMBIGUITY", PURPLE, 13, 0.72, "Retired: gene model"),
        ("DISCOVERED", BLUE, 15, 0.82, "QC-retained discovery"),
    ]
    for status, color, size, alpha, label in classes:
        subset = [row for row in stats if row["primary_gene_status"] == status]
        x = [number(row, "interaction_log2fc") for row in subset]
        y = [-math.log10(max(number(row, "interaction_q"), 1e-300)) for row in subset]
        ax_a.scatter(x, y, s=size, c=color, alpha=alpha, edgecolors="none", label=label, rasterized=True)
    effect_cut = math.log2(1.5)
    ax_a.axhline(-math.log10(0.05), color=GRAY, linestyle="--", lw=0.8)
    ax_a.axvline(-effect_cut, color=GRAY, linestyle="--", lw=0.8)
    ax_a.axvline(effect_cut, color=GRAY, linestyle="--", lw=0.8)
    ax_a.set_xlabel("Cultivar × infection interaction, log2 fold change\n(Yurong1 response − Guiwei response)")
    ax_a.set_ylabel("−log10 genome-wide q")
    ax_a.legend(frameon=False, ncol=2, loc="upper left")
    ax_a.text(
        0.99,
        0.96,
        "19,445 tested  •  262 statistical candidates\n206 retained after mapping/model QC",
        transform=ax_a.transAxes,
        ha="right",
        va="top",
        fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=WHITE, edgecolor=LIGHT_GRAY),
    )
    panel_title(ax_a, "A", "Genome-wide interaction discovery and uniform gene QC")
    clean_axes(ax_a)

    legacy_sorted = sorted(legacy_joined, key=lambda pair: number(pair[0], "interaction_log2fc"))
    y = np.arange(len(legacy_sorted))
    effects = np.array([number(row, "interaction_log2fc") for row, _ in legacy_sorted])
    errors = np.array([1.96 * number(row, "interaction_lfc_se") for row, _ in legacy_sorted])
    colors = [VERMILLION if joined["mappability_status"] == "FAIL" else BLUE for _, joined in legacy_sorted]
    for yi, effect, error, color in zip(y, effects, errors, colors):
        ax_b.errorbar(effect, yi, xerr=error, fmt="o", color=color, ecolor=color,
                      capsize=2, markersize=4, lw=0.9)
    ax_b.axvline(0, color=GRAY, linestyle="--", lw=0.8)
    ax_b.set_yticks(y, [row["gene_id"] for row, _ in legacy_sorted])
    ax_b.set_xlabel("Re-estimated interaction log2 fold change (95% CI)")
    ax_b.set_ylim(-0.8, len(y) - 0.2)
    ax_b.text(
        0.99,
        0.02,
        "Orange: uniform mappability failure\nNo legacy gene had q < 0.05",
        transform=ax_b.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
        bbox=dict(boxstyle="round,pad=0.25", facecolor=WHITE, edgecolor=LIGHT_GRAY),
    )
    panel_title(ax_b, "B", "Legacy 18: formal genome-wide reassessment")
    clean_axes(ax_b, "x")

    ax_c.axis("off")
    panel_title(ax_c, "C", "Evidence attrition")
    boxes = [
        ("19,445\nexpressed genes tested", LIGHT_GRAY),
        ("262\nstatistical candidates", SKY),
        ("206\nmapping/model-QC retained", BLUE),
        ("16\npassed all internal gates", GREEN),
        ("0 overlap\n(2 external supports failed\ninternal robustness)", WHITE),
    ]
    y_positions = [0.82, 0.64, 0.46, 0.28, 0.06]
    for (label, color), ypos in zip(boxes, y_positions):
        edge = DARK if color == WHITE else "none"
        add_box(ax_c, (0.12, ypos), 0.66, 0.12, label, color, edge)
    for y0, y1 in zip(y_positions[:-1], y_positions[1:]):
        ax_c.annotate(
            "",
            xy=(0.45, y1 + 0.14),
            xytext=(0.45, y0),
            xycoords=ax_c.transAxes,
            arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=0.9),
        )
    save_figure(fig, "figure2_discovery_legacy")


def figure3_gene_convergence() -> None:
    robustness = [
        row
        for row in read_tsv("results/tables/Table3_internal_robustness.tsv")
        if row["entity_type"] == "gene"
    ]
    external = [
        row
        for row in read_tsv("results/tables/Table4_external_evaluation.tsv")
        if row["entity_type"] == "gene"
        and row["study"] == "PRJNA450886"
        and row["contrast"] == "primary_24h"
    ]
    assert len(robustness) == 206 and len(external) == 206
    robust_ids = {
        row["gene_id"] for row in robustness if row["internal_robustness_status"] == "PASS"
    }
    supported_ids = {
        row["gene_id"] for row in external if row["external_status"] == "cross_context_supported"
    }
    assert len(robust_ids) == 16 and len(supported_ids) == 2
    assert not (robust_ids & supported_ids)
    ext_counts = Counter(row["external_status"] for row in external)
    assert ext_counts == {
        "unsupported": 177,
        "not_testable": 22,
        "contradictory": 5,
        "cross_context_supported": 2,
    }
    assert sum(yes(row, "measurable") for row in external) == 184

    individual_gates = [
        ("Quantification", "quantification_pass"),
        ("edgeR method", "statistical_method_pass"),
        ("Expression filter", "filter_pass"),
        ("Leave-one-library-out", "leave_one_out_pass"),
    ]
    gate_values = [sum(yes(row, field) for row in robustness) for _, field in individual_gates]
    assert gate_values == [196, 19, 205, 125]
    joint_four = sum(all(yes(row, field) for _, field in individual_gates) for row in robustness)
    assert joint_four == 18

    fig = plt.figure(figsize=(8.4, 7.4), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[0.92, 1.35], width_ratios=[1.35, 1])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_c = fig.add_subplot(grid[0, 1])
    ax_b = fig.add_subplot(grid[1, :])

    labels = [item[0] for item in individual_gates] + ["All four gates", "+ observed mapping gate"]
    values = gate_values + [joint_four, len(robust_ids)]
    colors = [SKY, ORANGE, SKY, SKY, PURPLE, GREEN]
    y = np.arange(len(labels))
    ax_a.barh(y, values, color=colors, height=0.62)
    for yi, value in zip(y, values):
        ax_a.text(value + 3, yi, str(value), va="center", fontsize=7.5)
    ax_a.set_yticks(y, labels)
    ax_a.invert_yaxis()
    ax_a.set_xlim(0, 220)
    ax_a.set_xlabel("Candidates passing (of 206)")
    ax_a.text(
        0.98,
        0.04,
        "Individual-gate rows are not sequential attrition",
        transform=ax_a.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.8,
        color=GRAY,
    )
    panel_title(ax_a, "A", "Internal robustness gates")
    clean_axes(ax_a, "x")

    ax_c.set_xlim(0, 1)
    ax_c.set_ylim(0, 1)
    ax_c.axis("off")
    panel_title(ax_c, "B", "No gene-level convergence")
    ax_c.add_patch(Circle((0.28, 0.55), 0.22, transform=ax_c.transAxes,
                          facecolor=GREEN, alpha=0.75, edgecolor=DARK, lw=0.9))
    ax_c.add_patch(Circle((0.76, 0.55), 0.16, transform=ax_c.transAxes,
                          facecolor=BLUE, alpha=0.75, edgecolor=DARK, lw=0.9))
    ax_c.text(0.28, 0.55, "16\ninternal robust", transform=ax_c.transAxes,
              ha="center", va="center", fontweight="bold")
    ax_c.text(0.76, 0.55, "2\nexternal support", transform=ax_c.transAxes,
              ha="center", va="center", fontweight="bold")
    ax_c.text(0.52, 0.16, "overlap = 0", transform=ax_c.transAxes,
              ha="center", va="center", fontsize=10, fontweight="bold", color=VERMILLION)
    ax_c.text(0.52, 0.04, "Primary external study is cross-context, not direct replication",
              transform=ax_c.transAxes, ha="center", va="bottom", fontsize=6.8, color=GRAY)

    measurable = [row for row in external if yes(row, "measurable")]
    style = {
        "unsupported": (GRAY, 16, 0.45),
        "cross_context_supported": (BLUE, 45, 0.95),
        "contradictory": (VERMILLION, 45, 0.95),
    }
    for status in ["unsupported", "cross_context_supported", "contradictory"]:
        subset = [row for row in measurable if row["external_status"] == status]
        color, size, alpha = style[status]
        ax_b.scatter(
            [number(row, "discovery_interaction_log2fc") for row in subset],
            [number(row, "external_log2fc") for row in subset],
            color=color,
            s=size,
            alpha=alpha,
            edgecolor=WHITE if status != "unsupported" else "none",
            linewidth=0.5,
            zorder=2 if status == "unsupported" else 4,
            label=status.replace("cross_context_", "cross-context "),
        )
    robust_measurable = [row for row in measurable if row["gene_id"] in robust_ids]
    ax_b.scatter(
        [number(row, "discovery_interaction_log2fc") for row in robust_measurable],
        [number(row, "external_log2fc") for row in robust_measurable],
        s=72,
        facecolors="none",
        edgecolors=GREEN,
        linewidth=1.2,
        zorder=5,
        label="internally robust (outline)",
    )
    bounds = [
        number(row, field)
        for row in measurable
        for field in ("discovery_interaction_log2fc", "external_log2fc")
    ]
    lim = max(3.6, math.ceil(max(abs(value) for value in bounds) * 2) / 2)
    ax_b.plot([-lim, lim], [-lim, lim], color=LIGHT_GRAY, linestyle="--", lw=0.9, zorder=0)
    ax_b.axhline(0, color=LIGHT_GRAY, lw=0.7, zorder=0)
    ax_b.axvline(0, color=LIGHT_GRAY, lw=0.7, zorder=0)
    for row in measurable:
        if row["external_status"] == "cross_context_supported":
            ax_b.annotate(
                row["gene_id"],
                (number(row, "discovery_interaction_log2fc"), number(row, "external_log2fc")),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=6.7,
            )
    ax_b.set_xlim(-lim, lim)
    ax_b.set_ylim(-lim, lim)
    ax_b.set_xlabel("Discovery interaction log2 fold change\nYurong1 response − Guiwei response (leaf, 24 h)")
    ax_b.set_ylabel("Primary external interaction log2 fold change\nHeiye response − Guiwei response (pericarp, 24 h)")
    ax_b.legend(frameon=False, ncol=4, loc="upper center")
    ax_b.text(
        0.99,
        0.03,
        "184/206 measurable  •  2 supported  •  5 contradictory  •  177 unsupported  •  22 not testable",
        transform=ax_b.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
    )
    panel_title(ax_b, "C", "Discovery versus primary cross-context effects")
    clean_axes(ax_b)
    save_figure(fig, "figure3_robustness_external")


def figure4_pathways_signatures() -> None:
    robustness = [
        row
        for row in read_tsv("results/tables/Table3_internal_robustness.tsv")
        if row["entity_type"] == "pathway"
    ]
    signatures = [
        row
        for row in read_tsv(
            "results/figures/source_data/Figure5_pathway_signature_validation_source_data.tsv"
        )
        if row["panel"] == "C_signatures"
    ]
    assert len(robustness) == 6
    assert Counter(row["internal_pathway_robustness_status"] for row in robustness) == {
        "FAIL": 5,
        "PASS": 1,
    }
    assert len(signatures) == 7
    primary = next(row for row in signatures if row["contrast"] == "primary_24h")
    assert math.isclose(number(primary, "estimate"), 0.109333537101263)
    assert number(primary, "confidence_lower") < 0 < number(primary, "confidence_upper")

    fig = plt.figure(figsize=(8.3, 7.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[0.92, 1.1])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[1, 0])

    pathway_rows = sorted(robustness, key=lambda row: number(row, "primary_NES"))
    labels = [row["pathway"].split("|", 1)[-1].replace("Initiation", "initiation") for row in pathway_rows]
    values = [number(row, "primary_NES") for row in pathway_rows]
    colors = [GREEN if row["internal_pathway_robustness_status"] == "PASS" else GRAY for row in pathway_rows]
    y = np.arange(len(pathway_rows))
    ax_a.barh(y, values, color=colors, height=0.62)
    for yi, row in zip(y, pathway_rows):
        ax_a.text(
            2.35,
            yi,
            f"q={number(row, 'primary_q'):.3g}",
            va="center",
            ha="left",
            fontsize=6.8,
        )
    ax_a.axvline(0, color=DARK, lw=0.7)
    ax_a.set_yticks(y, labels)
    ax_a.set_xlabel("Discovery normalized enrichment score")
    ax_a.set_xlim(-2.75, 3.25)
    ax_a.legend(
        handles=[
            Line2D([0], [0], color=GREEN, lw=7, label="Passed all internal pathway gates"),
            Line2D([0], [0], color=GRAY, lw=7, label="Failed ≥1 internal gate"),
        ],
        frameon=False,
        ncol=2,
        loc="upper center",
    )
    ax_a.text(
        0.5,
        -0.15,
        "All 6 were unsupported in the primary external pathway evaluation",
        transform=ax_a.transAxes,
        ha="center",
        va="top",
        fontsize=7.0,
        color=GRAY,
        clip_on=False,
    )
    panel_title(ax_a, "A", "Only the circadian pathway passed internal robustness")
    clean_axes(ax_a, "x")

    label_map = {
        ("PRJNA450886", "primary_24h"): "Sun 2019, 24 h cultivar × infection (primary)",
        ("PRJNA450886", "secondary_6h"): "Sun 2019, 6 h cultivar × infection (secondary)",
        ("PRJNA450886", "secondary_48h"): "Sun 2019, 48 h cultivar × infection (secondary)",
        ("PRJNA922966", "primary_leaf_infection"): "Feizixiao leaf infection (generic transfer)",
        ("PRJNA922966", "secondary_fruit_infection"): "Feizixiao fruit infection (secondary)",
        ("PRJNA922966", "secondary_tissue_interaction"): "Leaf − fruit infection interaction (secondary)",
        ("PRJNA1090613", "exploratory_interaction"): "Guiwei / SFZ interaction (exploratory metadata)",
    }
    ordered_keys = [key for key in label_map if key[0] != "PRJNA1090613"]
    by_key = {(row["study"], row["contrast"]): row for row in signatures}
    ordered = [by_key[key] for key in ordered_keys]
    y = np.arange(len(ordered))[::-1]
    role_color = {
        "primary_cross_context": ORANGE,
        "generic_infection_transfer": BLUE,
        "exploratory_only": GRAY,
    }
    for yi, key, row in zip(y, ordered_keys, ordered):
        estimate = number(row, "estimate")
        lower = number(row, "confidence_lower")
        upper = number(row, "confidence_upper")
        color = role_color[row["study_role"]]
        filled = number(row, "q") < 0.05
        ax_b.errorbar(
            estimate,
            yi,
            xerr=[[estimate - lower], [upper - estimate]],
            fmt="o",
            color=color,
            ecolor=color,
            markerfacecolor=color if filled else WHITE,
            markeredgecolor=color,
            markersize=5.2,
            capsize=2.5,
            lw=1.1,
        )
        ax_b.text(0.47, yi, f"q={number(row, 'q'):.3g}", va="center", fontsize=6.8)
    ax_b.axvline(0, color=DARK, linestyle="--", lw=0.8)
    ax_b.axhline(2.5, color=LIGHT_GRAY, lw=0.7)
    ax_b.set_yticks(y, [label_map[key] for key in ordered_keys])
    ax_b.set_xlabel("Signed 206-gene score estimate (95% CI)")
    ax_b.set_xlim(-0.5, 0.57)
    ax_b.text(
        0.5,
        -0.16,
        "Filled points: q < 0.05  •  exploratory PRJNA1090613 estimate moved to Figure S3",
        transform=ax_b.transAxes,
        ha="center",
        va="top",
        fontsize=6.8,
        color=GRAY,
        clip_on=False,
    )
    panel_title(ax_b, "B", "The signed discovery score changed with time and tissue")
    clean_axes(ax_b, "x")
    save_figure(fig, "figure4_pathways_signatures")


def figure5_dtu_orthogonal() -> None:
    dtu = read_tsv(
        "results/figures/source_data/Figure6_conditional_dtu_source_data.tsv"
    )
    discovery = [row for row in dtu if row["panel"] == "A_discovery_DTU"]
    discovered = [row for row in discovery if row["dtu_status"] == "DISCOVERED"]
    assert len(discovery) == 15_790
    assert len(discovered) == 225
    assert len({row["gene_id"] for row in discovered}) == 152
    external = [row for row in dtu if row["panel"] == "B_external_DTU"]
    expected_dtu = {
        "PRJNA450886": {"unsupported": 125, "not_testable": 100},
        "PRJNA922966": {"not_testable": 225},
        "PRJNA1090613": {
            "cross_context_supported": 4,
            "contradictory": 5,
            "unsupported": 101,
            "not_testable": 115,
        },
    }
    for study, expected in expected_dtu.items():
        observed = Counter(
            row["external_dtu_status"] for row in external if row["study"] == study
        )
        assert observed == expected, (study, observed, expected)

    annotation = read_tsv("results/supplement/S8_annotation_orthology.tsv")
    assert len(annotation) == 206
    annotation_counts = Counter(row["annotation_status"] for row in annotation)
    assert annotation_counts == {"FAMILY_LEVEL_FUNCTION": 150, "UNANNOTATED": 56}
    assert sum(row["high_confidence_annotation"] == "True" for row in annotation) == 0
    assert Counter(row["interpro_status"] for row in annotation) == {
        "NO_PRECOMPUTED_MATCH_SUBMIT_INTERPROSCAN": 206
    }

    orthogonal = read_tsv(
        "results/figures/source_data/Figure7_orthogonal_support_source_data.tsv"
    )
    motifs = [row for row in orthogonal if row["panel"] == "C_discovery_motifs"]
    small_rna = next(row for row in orthogonal if row["panel"] == "B_small_RNA")
    assert len(motifs) == 927
    assert Counter(row["discovery_motif_status"] for row in motifs) == {"NOT_ROBUST": 927}
    max_ame_1k = max(int(row["ame_pass_count_1000bp"]) for row in motifs)
    max_ame_2k = max(int(row["ame_pass_count_2000bp"]) for row in motifs)
    assert (max_ame_1k, max_ame_2k) == (4, 4)
    assert max(int(row["fimo_pass_count_1000bp"]) for row in motifs) == 0
    assert max(int(row["fimo_pass_count_2000bp"]) for row in motifs) == 0
    assert int(small_rna["exact_litchi_species_entries"]) == 0
    assert small_rna["reference_gate_status"] == "NOT_TESTABLE_REFERENCE_ABSENT"

    tiers = read_tsv("results/candidates/tier_summary.tsv")
    tier_counts = {row["tier"]: int(row["count"]) for row in tiers}
    assert tier_counts == {
        "Tier A": 0,
        "Tier B": 12,
        "Tier C": 0,
        "Exploratory": 191,
        "Retired": 65,
    }

    fig = plt.figure(figsize=(8.5, 8.0), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=[0.78, 1.03, 0.95])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_c = fig.add_subplot(grid[0, 1])
    ax_b = fig.add_subplot(grid[1, :])
    ax_d = fig.add_subplot(grid[2, 0])
    ax_e = fig.add_subplot(grid[2, 1])

    ax_a.axis("off")
    panel_title(ax_a, "A", "Conditional DTU discovery")
    add_box(ax_a, (0.00, 0.39), 0.29, 0.36, "15,790\ntranscripts\ntested", LIGHT_GRAY, fontsize=7.2)
    add_box(ax_a, (0.355, 0.39), 0.29, 0.36, "225\nDTU transcript\nevents", SKY, fontsize=7.2)
    add_box(ax_a, (0.71, 0.39), 0.27, 0.36, "152\ngenes", BLUE, fontsize=7.2)
    for x0, x1 in [(0.29, 0.355), (0.645, 0.71)]:
        ax_a.annotate("", xy=(x1, 0.56), xytext=(x0, 0.56), xycoords=ax_a.transAxes,
                      arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=0.9))
    ax_a.text(0.5, 0.16, "Stage-wise q values and signed usage-interaction differences",
              transform=ax_a.transAxes, ha="center", va="center", fontsize=6.8, color=GRAY)

    ax_c.set_xlim(0, 206)
    ax_c.set_ylim(-0.6, 1.6)
    ax_c.barh(1, 150, color=BLUE, height=0.48, label="Family-level function")
    ax_c.barh(1, 56, left=150, color=LIGHT_GRAY, height=0.48, label="Unannotated")
    ax_c.text(75, 1, "150", color=WHITE, ha="center", va="center", fontweight="bold")
    ax_c.text(178, 1, "56", color=DARK, ha="center", va="center", fontweight="bold")
    ax_c.barh(0, 0, color=GREEN, height=0.48)
    ax_c.text(3, 0, "0 high-confidence annotations", ha="left", va="center", color=VERMILLION,
              fontweight="bold")
    ax_c.set_yticks([1, 0], ["Provisional sequence evidence", "High-confidence gate"])
    ax_c.set_xlabel("QC-retained genes (n=206)")
    ax_c.legend(frameon=False, ncol=2, loc="lower right")
    ax_c.text(0.99, 0.96, "InterPro architecture unresolved for 206/206",
              transform=ax_c.transAxes, ha="right", va="top", fontsize=6.8, color=GRAY)
    panel_title(ax_c, "B", "Annotation remained provisional")
    clean_axes(ax_c, "x")

    studies = ["PRJNA450886", "PRJNA922966", "PRJNA1090613"]
    study_labels = [
        "Primary cross-context\nPRJNA450886",
        "Generic transfer\nPRJNA922966",
        "Exploratory only\nPRJNA1090613",
    ]
    statuses = ["cross_context_supported", "contradictory", "unsupported", "not_testable"]
    status_labels = ["Supported", "Contradictory", "Unsupported", "Not testable"]
    status_colors = [BLUE, VERMILLION, GRAY, LIGHT_GRAY]
    left = np.zeros(len(studies))
    y = np.arange(len(studies))
    for status, label, color in zip(statuses, status_labels, status_colors):
        values = np.array(
            [
                sum(
                    row["study"] == study and row["external_dtu_status"] == status
                    for row in external
                )
                for study in studies
            ]
        )
        ax_b.barh(y, values, left=left, color=color, height=0.62, label=label)
        for yi, value, start in zip(y, values, left):
            if value >= 4:
                ax_b.text(start + value / 2, yi, str(int(value)), ha="center", va="center",
                          fontsize=7.2, color=WHITE if color in {BLUE, VERMILLION, GRAY} else DARK)
        left += values
    ax_b.set_yticks(y, study_labels)
    ax_b.set_ylim(2.5, -0.95)
    ax_b.set_xlim(0, 225)
    ax_b.set_xlabel("Discovery DTU transcript events (n=225 per study)")
    ax_b.legend(frameon=False, ncol=4, loc="upper center")
    ax_b.text(
        0.5,
        -0.17,
        "Exploratory 4 supported / 5 contradictory events are not confirmatory; no primary event was supported",
        transform=ax_b.transAxes,
        ha="center",
        va="top",
        fontsize=6.9,
        color=GRAY,
        clip_on=False,
    )
    panel_title(ax_b, "C", "DTU follow-up was kept separate by study role")
    clean_axes(ax_b, "x")

    motif_values = [max_ame_1k, max_ame_2k]
    x = np.arange(2)
    ax_d.bar(x, motif_values, color=PURPLE, width=0.58, label="Maximum observed")
    ax_d.axhline(80, color=VERMILLION, linestyle="--", lw=1.0, label="Required robustness: 80/100")
    for xi, value in zip(x, motif_values):
        ax_d.text(xi, value + 3, f"{value}/100", ha="center", va="bottom", fontsize=7.2)
    ax_d.set_xticks(x, ["1 kb promoters", "2 kb promoters"])
    ax_d.set_ylabel("Matched backgrounds passing AME")
    ax_d.set_ylim(0, 105)
    ax_d.legend(frameon=False, loc="upper center")
    ax_d.text(
        0.98,
        0.46,
        "927 profiles tested\n0 robust motifs\n0 FIMO passes",
        transform=ax_d.transAxes,
        ha="right",
        va="center",
        fontsize=7.2,
    )
    ax_d.text(
        0.98,
        0.24,
        "Small-RNA pairing: not testable\n(0 exact Litchi reference entries)",
        transform=ax_d.transAxes,
        ha="right",
        va="center",
        fontsize=6.8,
        color=GRAY,
    )
    panel_title(ax_d, "D", "Orthogonal gates exposed reference limitations")
    clean_axes(ax_d, "y")

    order = ["Tier A", "Tier B", "Tier C", "Exploratory", "Retired"]
    values = [tier_counts[label] for label in order]
    colors = [GREEN, BLUE, GREEN, GRAY, LIGHT_GRAY]
    y = np.arange(len(order))
    ax_e.barh(y, values, color=colors, height=0.62)
    for yi, value in zip(y, values):
        ax_e.text(value + 3, yi, str(value), va="center", fontsize=7.5)
    ax_e.set_yticks(y, order)
    ax_e.invert_yaxis()
    ax_e.set_xlim(0, 210)
    ax_e.set_xlabel("Genes and pathways (n=268)")
    panel_title(ax_e, "E", "Final tiers preserved evidence boundaries")
    clean_axes(ax_e, "x")
    save_figure(fig, "figure5_dtu_orthogonal")


def main() -> None:
    figure1_cohorts_qc()
    figure2_discovery_legacy()
    figure3_gene_convergence()
    figure4_pathways_signatures()
    generate_h7_figures(ROOT, OUT)
    print(f"Wrote six main figures plus Figure S3 as PDF and PNG to {OUT}")


if __name__ == "__main__":
    main()
