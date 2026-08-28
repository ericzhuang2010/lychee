"""Generate the H7 split transcript-usage and orthogonal-evidence figures."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DARK = "#1F2937"
GRAY = "#6B7280"
LIGHT_GRAY = "#D1D5DB"
WHITE = "#FFFFFF"
BLUE = "#0072B2"
SKY = "#56B4E9"
GREEN = "#009E73"
VERMILLION = "#D55E00"
PURPLE = "#7B2CBF"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def save(fig: plt.Figure, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(out / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def panel_title(ax: plt.Axes, label: str, title: str) -> None:
    ax.set_title(f"{label}   {title}", loc="left", fontsize=9.2, fontweight="bold", pad=7)


def clean_axes(ax: plt.Axes, keep: str = "x") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if keep == "x":
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    elif keep == "y":
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(axis="x", length=0)


def add_box(ax: plt.Axes, xy: tuple[float, float], width: float, height: float, text: str, color: str) -> None:
    rectangle = plt.Rectangle(xy, width, height, transform=ax.transAxes, facecolor=color, edgecolor="none")
    ax.add_patch(rectangle)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, transform=ax.transAxes,
            ha="center", va="center", color=WHITE if color in {BLUE, SKY} else DARK,
            fontsize=8.0, fontweight="bold")


def generate_h7_figures(root: Path, out: Path) -> None:
    dtu = read_tsv(root / "results/figures/source_data/Figure6_conditional_dtu_source_data.tsv")
    discovery = [row for row in dtu if row["panel"] == "A_discovery_DTU"]
    discovered = [row for row in discovery if row["dtu_status"] == "DISCOVERED"]
    external = [row for row in dtu if row["panel"] == "B_external_DTU"]
    assert len(discovery) == 15_790
    assert len(discovered) == 225
    assert len({row["gene_id"] for row in discovered}) == 152
    expected_dtu = {
        "PRJNA450886": {"unsupported": 125, "not_testable": 100},
        "PRJNA922966": {"not_testable": 225},
        "PRJNA1090613": {"cross_context_supported": 4, "contradictory": 5, "unsupported": 101, "not_testable": 115},
    }
    for study, expected in expected_dtu.items():
        assert Counter(row["external_dtu_status"] for row in external if row["study"] == study) == expected

    fig = plt.figure(figsize=(8.4, 5.7), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[0.75, 1.25])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_a.axis("off")
    panel_title(ax_a, "A", "Conditional DTU discovery")
    add_box(ax_a, (0.06, 0.35), 0.24, 0.38, "15,790\ntranscripts tested", LIGHT_GRAY)
    add_box(ax_a, (0.39, 0.35), 0.24, 0.38, "225\nDTU events", SKY)
    add_box(ax_a, (0.72, 0.35), 0.22, 0.38, "152\ngenes", BLUE)
    for x0, x1 in ((0.30, 0.39), (0.63, 0.72)):
        ax_a.annotate("", xy=(x1, 0.54), xytext=(x0, 0.54), xycoords=ax_a.transAxes,
                      arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.0))
    ax_a.text(0.5, 0.13, "Stage-wise q values and signed usage-interaction differences",
              transform=ax_a.transAxes, ha="center", color=GRAY, fontsize=7.2)

    studies = ["PRJNA450886", "PRJNA922966", "PRJNA1090613"]
    study_labels = ["Primary cross-context\nPRJNA450886", "Generic transfer\nPRJNA922966", "Exploratory only\nPRJNA1090613"]
    statuses = ["cross_context_supported", "contradictory", "unsupported", "not_testable"]
    labels = ["Supported", "Contradictory", "Unsupported", "Not testable"]
    colors = [BLUE, VERMILLION, GRAY, LIGHT_GRAY]
    left = np.zeros(len(studies))
    y = np.arange(len(studies))
    for status, label, color in zip(statuses, labels, colors):
        values = np.array([sum(row["study"] == study and row["external_dtu_status"] == status for row in external) for study in studies])
        ax_b.barh(y, values, left=left, color=color, height=0.62, label=label)
        for yi, value, start in zip(y, values, left):
            if value >= 4:
                ax_b.text(start + value / 2, yi, str(int(value)), ha="center", va="center", fontsize=7.2,
                          color=WHITE if color in {BLUE, VERMILLION, GRAY} else DARK)
        left += values
    ax_b.set_yticks(y, study_labels)
    ax_b.set_ylim(2.5, -0.7)
    ax_b.set_xlim(0, 225)
    ax_b.set_xlabel("Discovery DTU transcript events (n=225 per study)")
    ax_b.legend(frameon=False, ncol=4, loc="upper center")
    ax_b.text(0.5, -0.20, "No primary event was supported; exploratory outcomes remain non-confirmatory.",
              transform=ax_b.transAxes, ha="center", fontsize=7.0, color=GRAY, clip_on=False)
    panel_title(ax_b, "B", "External DTU follow-up remained separated by study role")
    clean_axes(ax_b, "x")
    save(fig, out, "figure5_transcript_usage")

    annotation = read_tsv(root / "results/supplement/S8_annotation_orthology.tsv")
    annotation_counts = Counter(row["annotation_status"] for row in annotation)
    assert len(annotation) == 206 and annotation_counts == {"FAMILY_LEVEL_FUNCTION": 150, "UNANNOTATED": 56}
    assert sum(row["high_confidence_annotation"] == "True" for row in annotation) == 0
    orthogonal = read_tsv(root / "results/figures/source_data/Figure7_orthogonal_support_source_data.tsv")
    motifs = [row for row in orthogonal if row["panel"] == "C_discovery_motifs"]
    small_rna = next(row for row in orthogonal if row["panel"] == "B_small_RNA")
    assert len(motifs) == 927 and Counter(row["discovery_motif_status"] for row in motifs) == {"NOT_ROBUST": 927}
    max_ame_1k = max(int(row["ame_pass_count_1000bp"]) for row in motifs)
    max_ame_2k = max(int(row["ame_pass_count_2000bp"]) for row in motifs)
    assert (max_ame_1k, max_ame_2k) == (4, 4)
    assert int(small_rna["exact_litchi_species_entries"]) == 0
    tiers = {row["tier"]: int(row["count"]) for row in read_tsv(root / "results/candidates/tier_summary.tsv")}
    assert tiers == {"Tier A": 0, "Tier B": 12, "Tier C": 0, "Exploratory": 191, "Retired": 65}

    fig = plt.figure(figsize=(8.4, 6.5), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[0.92, 1.08])
    ax_a = fig.add_subplot(grid[0, :])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])
    ax_a.set_xlim(0, 206)
    ax_a.set_ylim(-0.6, 1.6)
    ax_a.barh(1, 150, color=BLUE, height=0.48, label="Family-level function")
    ax_a.barh(1, 56, left=150, color=LIGHT_GRAY, height=0.48, label="Unannotated")
    ax_a.text(75, 1, "150", color=WHITE, ha="center", va="center", fontweight="bold")
    ax_a.text(178, 1, "56", color=DARK, ha="center", va="center", fontweight="bold")
    ax_a.text(3, 0, "0 high-confidence annotations", ha="left", va="center", color=VERMILLION, fontweight="bold")
    ax_a.set_yticks([1, 0], ["Provisional sequence evidence", "High-confidence gate"])
    ax_a.set_xlabel("QC-retained genes (n=206)")
    ax_a.legend(frameon=False, ncol=2, loc="lower right")
    ax_a.text(0.99, 0.96, "InterPro architecture unresolved for 206/206", transform=ax_a.transAxes,
              ha="right", va="top", fontsize=7.0, color=GRAY)
    panel_title(ax_a, "A", "Annotation remained provisional")
    clean_axes(ax_a, "x")

    x = np.arange(2)
    ax_b.bar(x, [max_ame_1k, max_ame_2k], color=PURPLE, width=0.58)
    ax_b.axhline(80, color=VERMILLION, linestyle="--", lw=1.0, label="Required: 80/100")
    for xi, value in zip(x, [max_ame_1k, max_ame_2k]):
        ax_b.text(xi, value + 3, f"{value}/100", ha="center", fontsize=7.2)
    ax_b.set_xticks(x, ["1 kb", "2 kb"])
    ax_b.set_ylabel("Matched backgrounds passing AME")
    ax_b.set_ylim(0, 105)
    ax_b.legend(frameon=False, loc="upper center")
    ax_b.text(0.98, 0.43, "927 profiles; 0 robust motifs\n0 FIMO passes", transform=ax_b.transAxes,
              ha="right", fontsize=7.1)
    ax_b.text(0.98, 0.22, "Small RNA: not testable\n(0 exact Litchi entries)", transform=ax_b.transAxes,
              ha="right", fontsize=6.8, color=GRAY)
    panel_title(ax_b, "B", "Orthogonal gates exposed reference limitations")
    clean_axes(ax_b, "y")

    order = ["Tier A", "Tier B", "Tier C", "Exploratory", "Retired"]
    values = [tiers[label] for label in order]
    y = np.arange(len(order))
    ax_c.barh(y, values, color=[GREEN, BLUE, GREEN, GRAY, LIGHT_GRAY], height=0.62)
    for yi, value in zip(y, values):
        ax_c.text(value + 3, yi, str(value), va="center", fontsize=7.5)
    ax_c.set_yticks(y, order)
    ax_c.invert_yaxis()
    ax_c.set_xlim(0, 210)
    ax_c.set_xlabel("Genes and pathways (n=268)")
    panel_title(ax_c, "C", "Final tiers preserved evidence boundaries")
    clean_axes(ax_c, "x")
    save(fig, out, "figure6_orthogonal_tiers")

    signatures = [
        row for row in read_tsv(root / "results/figures/source_data/Figure5_pathway_signature_validation_source_data.tsv")
        if row["panel"] == "C_signatures" and row["study"] == "PRJNA1090613"
    ]
    assert len(signatures) == 1
    row = signatures[0]
    estimate = float(row["estimate"])
    lower = float(row["confidence_lower"])
    upper = float(row["confidence_upper"])
    fig, ax = plt.subplots(figsize=(6.2, 2.4), constrained_layout=True)
    ax.errorbar(estimate, 0, xerr=[[estimate - lower], [upper - estimate]], fmt="o", color=GRAY,
                markerfacecolor=GRAY if float(row["q"]) < 0.05 else WHITE, capsize=3)
    ax.axvline(0, color=DARK, linestyle="--", lw=0.8)
    ax.set_yticks([0], ["PRJNA1090613 Guiwei/SFZ interaction"])
    ax.set_xlabel("Signed 206-gene score estimate (95% CI)")
    ax.text(estimate, 0.18, f"q={float(row['q']):.3g}", ha="center", fontsize=7.2)
    ax.set_ylim(-0.45, 0.45)
    panel_title(ax, "S3", "Exploratory signature estimate (not confirmatory)")
    clean_axes(ax, "x")
    save(fig, out, "figureS3_exploratory_signature")
